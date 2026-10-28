"""
Notifications and Persistent Active Alerts API Endpoints.
Provides endpoints for retrieving active, blocking alerts in the app and dismissing them.
Enforces tenant isolation (IDOR mitigation) through get_current_user.
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.exceptions import ResourceNotFoundException
from app.db.session import get_db_session
from app.modules.audit.service import AuditService
from app.modules.notifications.models import Notification
from app.modules.url_scanning.models import ScannedUrl
from app.modules.users.models import User

router = APIRouter(prefix="/notifications", tags=["Notifications & Active Alerts"])


class ActiveAlertItem(BaseModel):
    """Active alert payload to be displayed in the app's persistent modal."""

    alert_id: uuid.UUID
    alert_type: str
    created_at: datetime
    domain: str
    defanged_url: str
    verdict: str
    risk_score: int
    impersonated_brand: str | None
    reasons: list[str]


def defang_url(url: str) -> str:
    """Replaces http with hxxp and dots with [.] to defang malicious URLs."""
    return url.replace("https://", "hxxps://").replace("http://", "hxxp://").replace(".", "[.]")


@router.get("/active", status_code=status.HTTP_200_OK)
async def get_active_alerts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """
    Returns all un-dismissed, active alerts for the authenticated user.
    The app displays a persistent warning modal for these alerts until dismissed.
    """
    stmt = (
        select(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_dismissed.is_(False),
        )
        .options(
            selectinload(Notification.url).selectinload(ScannedUrl.threat_assessment),
        )
        .order_by(desc(Notification.created_at))
    )

    result = await db.execute(stmt)
    notifications = result.scalars().all()

    active_alerts: list[dict[str, Any]] = []
    for notif in notifications:
        scanned_url = notif.url
        assessment = scanned_url.threat_assessment if scanned_url else None

        active_alerts.append(
            {
                "alert_id": str(notif.id),
                "alert_type": notif.alert_type,
                "created_at": notif.created_at.isoformat(),
                "domain": scanned_url.domain if scanned_url else "Unknown",
                "defanged_url": defang_url(scanned_url.canonical_url) if scanned_url else "",
                "verdict": assessment.verdict if assessment else "UNKNOWN",
                "risk_score": assessment.risk_score if assessment else 0,
                "impersonated_brand": assessment.impersonated_brand if assessment else None,
                "reasons": assessment.reasons if assessment else [],
            }
        )

    return {
        "success": True,
        "has_active_alerts": len(active_alerts) > 0,
        "count": len(active_alerts),
        "data": active_alerts,
    }


@router.post("/{notification_id}/dismiss", status_code=status.HTTP_200_OK)
async def dismiss_alert(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """
    Dismisses an active alert.
    Enforces tenant ownership check (Anti-IDOR: only owning user can dismiss their alert).
    """
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()

    if not notification:
        raise ResourceNotFoundException("Ogohlantirish topilmadi.")

    notification.is_dismissed = True
    notification.dismissed_at = datetime.now(UTC)
    await db.commit()

    await AuditService.log_event(
        db=db,
        action="ALERT_DISMISSED",
        user_id=current_user.id,
        details={"alert_id": str(notification.id)},
    )

    return {
        "success": True,
        "message": "Ogohlantirish muvaffaqiyatli o'chirildi.",
        "data": {
            "alert_id": str(notification.id),
            "is_dismissed": True,
            "dismissed_at": notification.dismissed_at.isoformat(),
        },
    }
