"""
Notification domain model.
Tracks alert delivery attempts, deduplication records, active persistent alerts,
and user acknowledgment/dismissal status.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.url_scanning.models import ScannedUrl
    from app.modules.users.models import User


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Notification delivery and active persistent alert entity."""

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scanned_urls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)  # CRITICAL_PHISHING, SCAM_WARNING
    delivery_status: Mapped[str] = mapped_column(
        String(32),
        default="PENDING",
        index=True,
        nullable=False,
    )  # PENDING, SENT, FAILED, THROTTLED

    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --------------------------------------------------------------------------
    # Persistent Active Alert Tracking in the App
    # --------------------------------------------------------------------------
    # True if the user explicitly clicked "Dismiss / Delete" in the App
    is_dismissed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
        nullable=False,
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    url: Mapped["ScannedUrl"] = relationship("ScannedUrl", back_populates="notifications")

    def __repr__(self) -> str:
        return (
            f"<Notification id={self.id} user_id={self.user_id} "
            f"delivery={self.delivery_status} dismissed={self.is_dismissed}>"
        )
