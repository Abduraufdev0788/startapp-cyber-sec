"""
Telethon Real-time Monitoring Daemon.
Loads connected Telegram user accounts from PostgreSQL, decrypts sessions from AES-256-GCM in RAM,
listens for incoming and edited messages across joined groups/channels, routes detected URLs to Celery scanner,
and listens for dynamic account connect/disconnect events via Redis PubSub.
"""

import asyncio
import json
import logging
import signal
import uuid
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy import select
from telethon import TelegramClient, events
from telethon.errors import AuthKeyUnregisteredError, SessionRevokedError
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.security import decrypt_field
from app.db.session import get_standalone_db_session
from app.modules.telegram_accounts.models import TelegramAccount
from app.modules.url_scanning.pipeline import canonicalize_url, extract_urls_from_text
from app.modules.users.models import User  # noqa: F401

logger = logging.getLogger(__name__)


def extract_all_urls_from_event(event: events.NewMessage.Event) -> set[str]:
    """
    Extracts all URLs from:
    1. Message text and media captions (MessageEntityUrl)
    2. Hyperlinks hidden behind words (MessageEntityTextUrl)
    3. Inline keyboard buttons
    4. Raw text via regular expressions fallback
    """
    urls: set[str] = set()
    message = event.message
    text = message.message or ""

    # 1. Extract from official Telegram entities (open URLs and hidden text URLs)
    if message.entities:
        for entity in message.entities:
            if isinstance(entity, MessageEntityUrl):
                offset = entity.offset
                length = entity.length
                url_str = text[offset : offset + length]
                urls.add(url_str)
            elif isinstance(entity, MessageEntityTextUrl):
                urls.add(entity.url)

    # 2. Extract from Inline Keyboard Markup buttons
    if hasattr(message, "buttons") and message.buttons:
        for row in message.buttons:
            for button in row:
                btn_url = getattr(button, "url", None) or (
                    getattr(button.type, "url", None) if hasattr(button, "type") else None
                )
                if btn_url:
                    urls.add(btn_url)
    elif message.reply_markup and hasattr(message.reply_markup, "rows"):
        for row in message.reply_markup.rows:
            for button in getattr(row, "buttons", []):
                btn_url = getattr(button, "url", None) or (
                    getattr(button.type, "url", None) if hasattr(button, "type") else None
                )
                if btn_url:
                    urls.add(btn_url)

    # 3. Extract from raw text using regex fallback
    for regex_url in extract_urls_from_text(text):
        urls.add(regex_url)

    return urls


class TelethonMonitorManager:
    """Manages active Telethon client instances for all connected platform accounts."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.active_clients: dict[str, TelegramClient] = {}
        self.client_tasks: dict[str, asyncio.Task[None]] = {}
        self.is_running = False
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """Starts monitoring for all registered active accounts and listens for events."""
        self.is_running = True
        logger.info("Initializing Telethon Monitor Manager...")

        # 1. Load active accounts from DB
        try:
            async with get_standalone_db_session() as db:
                stmt = select(TelegramAccount).where(TelegramAccount.status == "CONNECTED")
                result = await db.execute(stmt)
                accounts = result.scalars().all()

            logger.info("Found %d active account(s) to monitor at startup.", len(accounts))
            for account in accounts:
                await self.start_account_monitor(account)
        except Exception as e:
            logger.error("Error loading accounts from database: %s", e)

        # 2. Start Redis listener in background for dynamic account additions/removals
        redis_task = asyncio.create_task(self._listen_for_redis_events())

        # 3. Main lifecycle wait
        try:
            await self._stop_event.wait()
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        finally:
            await self.shutdown()
            if not redis_task.done():
                redis_task.cancel()

    async def start_account_monitor(self, account: TelegramAccount) -> bool:
        """Initializes a Telethon client for an account and registers event handlers."""
        account_id_str = str(account.id)
        if account_id_str in self.active_clients:
            logger.info("Account %s is already being monitored.", account_id_str)
            return True

        try:
            # Decrypt Telethon session string in-memory with Associated Authenticated Data (AAD)
            decrypted_bytes = decrypt_field(
                envelope=account.encrypted_session,
                associated_data=str(account.user_id),
            )
            session_str = decrypted_bytes.decode("utf-8")

            client = TelegramClient(
                session=StringSession(session_str),
                api_id=self.settings.TELEGRAM_API_ID,
                api_hash=self.settings.TELEGRAM_API_HASH,
                auto_reconnect=True,
                connection_retries=10,
                retry_delay=5,
            )

            await client.connect()
            if not await client.is_user_authorized():
                logger.warning("Account %s session is not authorized. Marking as REVOKED.", account.id)
                await self._mark_account_revoked(account.id)
                await client.disconnect()
                return False

            me = await client.get_me()
            try:
                dialogs = await client.get_dialogs(limit=50)
                logger.info(
                    "Warmed up entity cache for account @%s with %d dialogs.",
                    getattr(me, "username", "N/A"),
                    len(dialogs),
                )
            except Exception as dialog_err:
                logger.warning("Could not warm up dialogs for account %s: %s", account.id, dialog_err)

            self._register_handlers(client, account.user_id, account.telegram_user_id)
            self.active_clients[account_id_str] = client

            # Launch supervised background runner
            task = asyncio.create_task(self._run_client(client, account.id))
            self.client_tasks[account_id_str] = task

            logger.info(
                "Started monitor for account: @%s (TG ID: %s, Account ID: %s)",
                getattr(me, "username", "N/A"),
                me.id,
                account_id_str,
            )
            return True
        except Exception as e:
            logger.error("Failed to start monitor for account %s: %s", account.id, str(e), exc_info=True)
            return False

    async def _run_client(self, client: TelegramClient, account_id: uuid.UUID) -> None:
        """Supervises a running Telethon client until disconnected or revoked."""
        account_id_str = str(account_id)
        try:
            await client.run_until_disconnected()
        except (AuthKeyUnregisteredError, SessionRevokedError):
            logger.warning("Session for account %s was revoked remotely by the user.", account_id)
            await self._mark_account_revoked(account_id)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Unexpected error in monitor client for account %s: %s", account_id, e)
        finally:
            self.active_clients.pop(account_id_str, None)
            self.client_tasks.pop(account_id_str, None)

    async def stop_account_monitor(self, account_id_str: str) -> None:
        """Disconnects an active client and cancels its background task."""
        client = self.active_clients.pop(account_id_str, None)
        task = self.client_tasks.pop(account_id_str, None)

        if client:
            try:
                await client.disconnect()
            except Exception as e:
                logger.debug("Error disconnecting client %s: %s", account_id_str, e)

        if task and not task.done():
            task.cancel()
        logger.info("Stopped monitoring for account %s.", account_id_str)

    async def _mark_account_revoked(self, account_id: uuid.UUID) -> None:
        """Updates account status in database to REVOKED upon session termination."""
        try:
            async with get_standalone_db_session() as db:
                stmt = select(TelegramAccount).where(TelegramAccount.id == account_id)
                account = (await db.execute(stmt)).scalar_one_or_none()
                if account:
                    account.status = "REVOKED"
                    account.auth_state = "EXPIRED"
                    await db.commit()
                    logger.info("Marked account %s as REVOKED in database.", account_id)
        except Exception as e:
            logger.error("Failed to mark account %s as REVOKED: %s", account_id, e)

    async def _listen_for_redis_events(self) -> None:
        """Listens for dynamic account connect/disconnect events from Redis PubSub."""
        logger.info("Starting Redis PubSub listener for account events...")
        while self.is_running:
            redis_client = None
            pubsub = None
            try:
                redis_client = aioredis.from_url(self.settings.REDIS_URL, decode_responses=True)
                pubsub = redis_client.pubsub()
                await pubsub.subscribe("telegram:account_events")

                while self.is_running:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message.get("type") == "message":
                        data_str = message.get("data")
                        if data_str:
                            await self._handle_account_event(json.loads(data_str))
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Redis PubSub listener error: %s. Reconnecting in 5s...", e)
                await asyncio.sleep(5)
            finally:
                if pubsub:
                    try:
                        await pubsub.unsubscribe("telegram:account_events")
                        await pubsub.aclose()
                    except Exception:
                        pass
                if redis_client:
                    try:
                        await redis_client.aclose()
                    except Exception:
                        pass

    async def _handle_account_event(self, event_data: dict[str, Any]) -> None:
        """Processes account connect/disconnect events."""
        action = event_data.get("action")
        account_id_str = event_data.get("account_id")
        if not account_id_str:
            return

        logger.info("Received account event: %s for account: %s", action, account_id_str)
        if action == "ACCOUNT_CONNECTED":
            try:
                acc_uuid = uuid.UUID(account_id_str)
                async with get_standalone_db_session() as db:
                    stmt = select(TelegramAccount).where(TelegramAccount.id == acc_uuid)
                    account = (await db.execute(stmt)).scalar_one_or_none()
                    if account and account.status == "CONNECTED":
                        await self.start_account_monitor(account)
            except Exception as e:
                logger.error("Failed to handle ACCOUNT_CONNECTED event: %s", e)

        elif action == "ACCOUNT_DISCONNECTED":
            await self.stop_account_monitor(account_id_str)

    def _register_handlers(self, client: TelegramClient, user_id: Any, telegram_user_id: int) -> None:
        """Attaches incoming and edited message event handlers to a Telethon client."""

        async def _handle_message_event(event: events.NewMessage.Event, event_type: str = "new") -> None:
            # Fast filter: Skip service or empty messages
            if not event.message or not (event.message.message or event.message.entities):
                return

            # Exclude messages sent by or chatting with our security bot to prevent recursive alerts
            bot_token = self.settings.TELEGRAM_BOT_TOKEN
            bot_id = int(bot_token.split(":")[0]) if bot_token and ":" in bot_token else None
            sender_id = getattr(event, "sender_id", None)
            if bot_id and (event.chat_id == bot_id or sender_id == bot_id):
                return

            chat = await event.get_chat()
            chat_title = getattr(chat, "title", None)
            if not chat_title:
                fn = getattr(chat, "first_name", "") or ""
                ln = getattr(chat, "last_name", "") or ""
                full_name = f"{fn} {ln}".strip()
                chat_title = full_name if full_name else getattr(chat, "username", "Shaxsiy chat")

            snippet = (event.message.message or "").replace("\n", " ")[:60]
            logger.info(
                "Telethon intercepted %s message in '%s' (chat_id=%s, out=%s): '%s'",
                event_type,
                chat_title,
                event.chat_id,
                getattr(event, "out", False),
                snippet,
            )

            urls = extract_all_urls_from_event(event)
            if not urls:
                return  # Skip messages without any URLs

            logger.info(
                "Detected %d URL(s) in %s message in chat '%s' for user %s (TG: %s): %s",
                len(urls),
                event_type,
                chat_title,
                user_id,
                telegram_user_id,
                urls,
            )

            # Route each URL to Celery scanning queue
            for raw_url in urls:
                canonical = canonicalize_url(raw_url)
                logger.info("Routing canonical URL to Celery scanner: %s (Chat: %s)", canonical, chat_title)
                try:
                    from app.workers.tasks.scan import scan_url_background
                    scan_url_background.delay(
                        canonical_url=canonical,
                        user_id_str=str(user_id),
                        chat_id=event.chat_id,
                        chat_title=chat_title,
                        user_telegram_id=telegram_user_id,
                    )
                except Exception as err:
                    logger.error("Failed to enqueue scan task: %s", str(err), exc_info=True)

        @client.on(events.NewMessage)
        async def on_new_message(event: events.NewMessage.Event) -> None:
            await _handle_message_event(event, event_type="new")

        @client.on(events.MessageEdited)
        async def on_message_edited(event: events.MessageEdited.Event) -> None:
            await _handle_message_event(event, event_type="edited")

    async def shutdown(self) -> None:
        """Gracefully disconnects all clients upon shutdown."""
        self.is_running = False
        self._stop_event.set()
        logger.info("Shutting down Telethon Monitor Manager...")
        account_ids = list(self.active_clients.keys())
        for acc_id in account_ids:
            await self.stop_account_monitor(acc_id)
        logger.info("Telethon Monitor Manager shutdown complete.")


async def main() -> None:
    """Daemon entrypoint."""
    setup_logging()
    manager = TelethonMonitorManager()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(manager.shutdown()))
        except NotImplementedError:
            pass

    await manager.start()


if __name__ == "__main__":
    asyncio.run(main())
