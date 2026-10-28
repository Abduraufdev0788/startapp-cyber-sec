"""
Celery notification dispatch task.
Delivers real-time Telegram alerts with deep link buttons to the user.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import get_standalone_db_session
from app.integrations.telegram_bot.bot import send_phishing_alert
from app.modules.notifications.models import Notification
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.workers.tasks.notify.dispatch_alert",
    max_retries=3,
    default_retry_delay=5,
    rate_limit="20/s",
)
def dispatch_alert_task(
    self,
    alert_id: str,
    chat_id: int,
    chat_title: str,
    defanged_url: str,
    risk_score: int,
    impersonated_brand: str | None,
    reasons: list[str],
) -> bool:
    """Dispatches the Telegram Bot alert synchronously within the Celery worker."""
    settings = get_settings()

    async def _send() -> bool:
        success = await send_phishing_alert(
            bot_token=settings.TELEGRAM_BOT_TOKEN,
            chat_id=chat_id,
            alert_id=alert_id,
            chat_title=chat_title,
            defanged_url=defanged_url,
            risk_score=risk_score,
            impersonated_brand=impersonated_brand,
            reasons=reasons,
        )

        # Update delivery status in PostgreSQL
        async with get_standalone_db_session() as db:
            stmt = select(Notification).where(Notification.id == uuid.UUID(alert_id))
            result = await db.execute(stmt)
            notif = result.scalar_one_or_none()
            if notif:
                notif.delivery_status = "SENT" if success else "FAILED"
                notif.attempts += 1
                if success:
                    notif.sent_at = datetime.now(UTC)
                await db.commit()

        return success

    return asyncio.run(_send())
