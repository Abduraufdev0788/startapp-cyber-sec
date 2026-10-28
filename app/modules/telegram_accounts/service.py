"""
Telegram Account Management Service.
Handles MTProto authentication handshake (code request, OTP verification, 2FA cloud passwords),
AES-256-GCM session envelope encryption, and session revocation.
"""

import json
import logging
import uuid
from typing import Any

import redis.asyncio as aioredis
from telethon import TelegramClient
from telethon.errors import (
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession

from app.core.config import get_settings
from app.core.exceptions import TelegramAuthException
from app.core.security import decrypt_field, encrypt_field, hash_phone_number
from app.db.session import get_standalone_db_session
from app.modules.telegram_accounts.models import TelegramAccount

logger = logging.getLogger(__name__)

# Fallback in-memory storage for active authentication handshakes
_AUTH_HANDSHAKES: dict[str, dict[str, Any]] = {}


class TelegramAccountService:
    """Orchestrates Telegram MTProto user-account authorization."""

    @classmethod
    async def _save_handshake(cls, phone: str, session_str: str, phone_code_hash: str) -> None:
        """Stores temporary handshake data in Redis (TTL: 10m) with in-memory fallback."""
        settings = get_settings()
        try:
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            payload = json.dumps({"session_str": session_str, "phone_code_hash": phone_code_hash})
            await r.set(f"tg_handshake:{phone}", payload, ex=600)
            await r.aclose()
        except Exception as e:
            logger.debug("Redis handshake store failed, using in-memory: %s", e)

    @classmethod
    async def _get_handshake(cls, phone: str) -> dict[str, str] | None:
        """Retrieves temporary handshake data from Redis or in-memory fallback."""
        if phone in _AUTH_HANDSHAKES:
            hs = _AUTH_HANDSHAKES[phone]
            return {
                "session_str": hs["session"].save() if hasattr(hs.get("session"), "save") else hs.get("session_str", ""),
                "phone_code_hash": hs.get("phone_code_hash", ""),
            }

        settings = get_settings()
        try:
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            data = await r.get(f"tg_handshake:{phone}")
            await r.aclose()
            if data:
                return json.loads(data)
        except Exception as e:
            logger.debug("Redis handshake lookup failed: %s", e)

        return None

    @classmethod
    async def _clear_handshake(cls, phone: str) -> None:
        """Cleans up temporary handshake data from Redis and memory."""
        _AUTH_HANDSHAKES.pop(phone, None)
        settings = get_settings()
        try:
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await r.delete(f"tg_handshake:{phone}")
            await r.aclose()
        except Exception:
            pass

    @classmethod
    async def send_code(cls, phone_number: str) -> dict[str, Any]:
        """
        Initiates Telegram login handshake:
        Creates a temporary Telethon StringSession and requests an OTP code from Telegram.
        """
        settings = get_settings()
        clean_phone = phone_number.strip().replace(" ", "").replace("-", "")

        session = StringSession()
        client = TelegramClient(session, settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH)
        await client.connect()

        try:
            sent_code = await client.send_code_request(clean_phone)
            session_str = session.save()

            # Store in-memory and in Redis
            _AUTH_HANDSHAKES[clean_phone] = {
                "client": client,
                "session": session,
                "session_str": session_str,
                "phone_code_hash": sent_code.phone_code_hash,
            }
            await cls._save_handshake(clean_phone, session_str, sent_code.phone_code_hash)

            logger.info("Telegram code sent successfully to phone: %s", clean_phone[:6] + "****")
            return {
                "phone_number": clean_phone,
                "phone_code_hash": sent_code.phone_code_hash,
                "status": "CODE_SENT",
                "message": "Tasdiqlash kodi Telegram ilovangizga yuborildi.",
            }
        except Exception as e:
            await client.disconnect()
            logger.error("Failed to send Telegram code: %s", str(e), exc_info=True)
            raise TelegramAuthException(f"Kodni yuborishda xatolik: {e}") from e

    @classmethod
    async def verify_code(
        cls,
        user_id: uuid.UUID,
        phone_number: str,
        phone_code_hash: str,
        code: str,
    ) -> dict[str, Any]:
        """
        Submits the OTP code to Telegram.
        If 2FA password is required, returns NEED_2FA.
        Otherwise, encrypts session with AES-256-GCM and persists to PostgreSQL.
        """
        clean_phone = phone_number.strip().replace(" ", "").replace("-", "")
        client = None

        if clean_phone in _AUTH_HANDSHAKES:
            client = _AUTH_HANDSHAKES[clean_phone]["client"]
        else:
            hs = await cls._get_handshake(clean_phone)
            if hs and hs.get("session_str"):
                settings = get_settings()
                client = TelegramClient(
                    StringSession(hs["session_str"]),
                    settings.TELEGRAM_API_ID,
                    settings.TELEGRAM_API_HASH,
                )
                await client.connect()
                _AUTH_HANDSHAKES[clean_phone] = {
                    "client": client,
                    "session_str": hs["session_str"],
                    "phone_code_hash": hs.get("phone_code_hash", phone_code_hash),
                }

        if not client:
            raise TelegramAuthException(
                "Autentifikatsiya sessiyasi topilmadi yoki muddati o'tgan. Iltimos, kodni qayta so'rang.",
                code="HANDSHAKE_EXPIRED",
            )

        try:
            await client.sign_in(
                phone=clean_phone,
                code=code,
                phone_code_hash=phone_code_hash,
            )
            # Login successful without 2FA
            return await cls._finalize_login(user_id, clean_phone, client)

        except SessionPasswordNeededError:
            logger.info("2FA password required for phone: %s", clean_phone[:6] + "****")
            # Update session in Redis/memory as it now holds partial 2FA state
            session_str = client.session.save()
            await cls._save_handshake(clean_phone, session_str, phone_code_hash)
            return {
                "phone_number": clean_phone,
                "status": "NEED_2FA",
                "message": "Akkauntingizda 2FA (ikki bosqichli bulutli parol) yoqilgan. Parolni kiriting.",
            }
        except PhoneCodeInvalidError as e:
            raise TelegramAuthException("Kiritilgan tasdiqlash kodi noto'g'ri.", code="PHONE_CODE_INVALID") from e
        except PhoneCodeExpiredError as e:
            raise TelegramAuthException("Tasdiqlash kodi muddati o'tgan. Qayta so'rang.", code="PHONE_CODE_EXPIRED") from e
        except Exception as e:
            logger.error("Error during code verification: %s", str(e), exc_info=True)
            raise TelegramAuthException(f"Kodni tasdiqlashda xatolik: {e}") from e

    @classmethod
    async def verify_2fa(
        cls,
        user_id: uuid.UUID,
        phone_number: str,
        password_2fa: str,
    ) -> dict[str, Any]:
        """
        Submits the 2FA cloud password to complete login.
        Encrypts session with AES-256-GCM and persists to PostgreSQL.
        Password is never logged or stored.
        """
        clean_phone = phone_number.strip().replace(" ", "").replace("-", "")
        client = None

        if clean_phone in _AUTH_HANDSHAKES:
            client = _AUTH_HANDSHAKES[clean_phone]["client"]
        else:
            hs = await cls._get_handshake(clean_phone)
            if hs and hs.get("session_str"):
                settings = get_settings()
                client = TelegramClient(
                    StringSession(hs["session_str"]),
                    settings.TELEGRAM_API_ID,
                    settings.TELEGRAM_API_HASH,
                )
                await client.connect()
                _AUTH_HANDSHAKES[clean_phone] = {
                    "client": client,
                    "session_str": hs["session_str"],
                    "phone_code_hash": hs.get("phone_code_hash", ""),
                }

        if not client:
            raise TelegramAuthException("Autentifikatsiya sessiyasi topilmadi. Qaytadan boshlang.")

        try:
            await client.sign_in(password=password_2fa)
            return await cls._finalize_login(user_id, clean_phone, client)
        except PasswordHashInvalidError as e:
            raise TelegramAuthException("Kiritilgan 2FA bulutli parol noto'g'ri.", code="PASSWORD_2FA_INVALID") from e
        except Exception as e:
            logger.error("Error during 2FA sign in: %s", str(e), exc_info=True)
            raise TelegramAuthException(f"2FA orqali kirishda xatolik: {e}") from e

    @classmethod
    async def _finalize_login(
        cls,
        user_id: uuid.UUID,
        clean_phone: str,
        client: TelegramClient,
    ) -> dict[str, Any]:
        """
        Extracts raw session string, encrypts it using AES-256-GCM bound to user_id,
        saves to PostgreSQL, syncs initial dialogs, and cleans up temporary handshake memory and Redis.
        """
        me = await client.get_me()
        session_str = client.session.save()

        # Clean up handshake state
        await cls._clear_handshake(clean_phone)

        # Encrypt session using AES-256-GCM with Associated Authenticated Data (AAD)
        encrypted_session = encrypt_field(
            plaintext=session_str,
            associated_data=str(user_id),
        )
        phone_hash = hash_phone_number(clean_phone)

        settings = get_settings()
        async with get_standalone_db_session() as db:
            account = TelegramAccount(
                user_id=user_id,
                telegram_user_id=me.id,
                phone_number_hash=phone_hash,
                encrypted_session=encrypted_session,
                status="CONNECTED",
                auth_state="AUTHORIZED",
            )
            db.add(account)
            await db.commit()
            account_id = account.id

            # Sync initial chats/channels while client is connected
            await cls.sync_dialogs(client=client, account_id=account.id, db=db, limit=50)

        # Disconnect handshake client
        await client.disconnect()

        # Publish event for real-time monitoring manager
        try:
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await r.publish(
                "telegram:account_events",
                json.dumps({
                    "action": "ACCOUNT_CONNECTED",
                    "account_id": str(account_id),
                    "user_id": str(user_id),
                    "telegram_user_id": me.id,
                }),
            )
            await r.aclose()
        except Exception as e:
            logger.debug("Failed to publish account_connected event to Redis: %s", e)

        logger.info(
            "Telegram account successfully registered and encrypted for user: %s (TG ID: %s)",
            user_id,
            me.id,
        )

        return {
            "account_id": str(account_id),
            "telegram_user_id": me.id,
            "first_name": me.first_name,
            "username": me.username,
            "status": "CONNECTED",
            "message": "Telegram hisobingiz muvaffaqiyatli ulandi va himoyalangan monitoring yoqildi.",
        }

    @classmethod
    async def disconnect_account(
        cls,
        account: TelegramAccount,
        user_id: uuid.UUID,
        db: Any,
    ) -> bool:
        """
        Officially revokes the active Telegram session via Telethon log_out()
        and removes the account from PostgreSQL.
        """
        settings = get_settings()
        account_id_str = str(account.id)
        try:
            session_bytes = decrypt_field(
                envelope=account.encrypted_session,
                associated_data=str(user_id),
            )
            session_str = session_bytes.decode("utf-8")
            client = TelegramClient(
                StringSession(session_str),
                settings.TELEGRAM_API_ID,
                settings.TELEGRAM_API_HASH,
            )
            await client.connect()
            if await client.is_user_authorized():
                await client.log_out()
                logger.info("Successfully revoked Telegram session remotely on Telegram servers for user %s", user_id)
            await client.disconnect()
        except Exception as e:
            logger.warning("Could not cleanly log_out Telegram session remotely: %s", e)

        await db.delete(account)
        await db.commit()

        # Publish event for real-time monitoring manager
        try:
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await r.publish(
                "telegram:account_events",
                json.dumps({
                    "action": "ACCOUNT_DISCONNECTED",
                    "account_id": account_id_str,
                    "user_id": str(user_id),
                }),
            )
            await r.aclose()
        except Exception as e:
            logger.debug("Failed to publish account_disconnected event to Redis: %s", e)

        return True

    @classmethod
    async def sync_dialogs(
        cls,
        client: TelegramClient,
        account_id: uuid.UUID,
        db: Any,
        limit: int = 50,
    ) -> int:
        """
        Discovers accessible dialogs (channels, supergroups, groups, private)
        and persists them into telegram_chats table.
        """
        from sqlalchemy import select

        from app.modules.telegram_chats.models import TelegramChat

        synced_count = 0
        try:
            dialogs = await client.get_dialogs(limit=limit)
            for dialog in dialogs:
                telegram_chat_id = dialog.id
                title = dialog.title or getattr(dialog.entity, "username", None) or "Telegram Chat"

                if dialog.is_channel:
                    chat_type = "CHANNEL" if getattr(dialog.entity, "broadcast", False) else "SUPERGROUP"
                elif dialog.is_group:
                    chat_type = "GROUP"
                else:
                    chat_type = "PRIVATE"

                stmt = select(TelegramChat).where(
                    TelegramChat.account_id == account_id,
                    TelegramChat.telegram_chat_id == telegram_chat_id,
                )
                existing = (await db.execute(stmt)).scalar_one_or_none()
                if not existing:
                    chat = TelegramChat(
                        account_id=account_id,
                        telegram_chat_id=telegram_chat_id,
                        title=title[:255],
                        type=chat_type,
                        is_monitored=True,
                    )
                    db.add(chat)
                    synced_count += 1
                else:
                    existing.title = title[:255]
                    existing.type = chat_type

            await db.commit()
            logger.info("Synced %d chats/channels for account %s", synced_count, account_id)
        except Exception as e:
            logger.warning("Failed to sync dialogs for account %s: %s", account_id, e)
        return synced_count

    @classmethod
    async def refresh_account_chats(
        cls,
        account: TelegramAccount,
        user_id: uuid.UUID,
        db: Any,
        limit: int = 100,
    ) -> int:
        """
        Decrypts account session, connects to Telegram, syncs dialogs, and disconnects.
        """
        settings = get_settings()
        session_bytes = decrypt_field(
            envelope=account.encrypted_session,
            associated_data=str(user_id),
        )
        session_str = session_bytes.decode("utf-8")
        client = TelegramClient(
            StringSession(session_str),
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH,
        )
        await client.connect()
        try:
            if not await client.is_user_authorized():
                raise TelegramAuthException("Sessiya avtorizatsiyadan o'tmagan.")
            return await cls.sync_dialogs(client=client, account_id=account.id, db=db, limit=limit)
        finally:
            await client.disconnect()

    @classmethod
    async def get_account_chats(
        cls,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
        db: Any,
    ) -> list[dict[str, Any]]:
        """Retrieves list of monitored chats for the given Telegram account."""
        from sqlalchemy import select

        from app.modules.telegram_chats.models import TelegramChat

        stmt = (
            select(TelegramChat)
            .join(TelegramAccount, TelegramAccount.id == TelegramChat.account_id)
            .where(
                TelegramChat.account_id == account_id,
                TelegramAccount.user_id == user_id,
            )
        )
        result = await db.execute(stmt)
        chats = result.scalars().all()
        return [
            {
                "chat_id": str(chat.id),
                "telegram_chat_id": chat.telegram_chat_id,
                "title": chat.title,
                "type": chat.type,
                "is_monitored": chat.is_monitored,
                "created_at": chat.created_at.isoformat() if chat.created_at else None,
            }
            for chat in chats
        ]
