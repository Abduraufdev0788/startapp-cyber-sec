"""
Scanned URL domain model.
Stores canonicalized URLs with fast SHA-256 hash index for deduplication and caching.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CHAR, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.notifications.models import Notification
    from app.modules.risk_engine.models import ThreatAssessment
    from app.modules.threat_intelligence.models import ThreatIntelligence


class ScannedUrl(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Canonicalized URL entity with status tracking."""

    __tablename__ = "scanned_urls"

    # Fast hash lookup: SHA-256 of canonical_url
    url_hash: Mapped[str] = mapped_column(CHAR(64), unique=True, index=True, nullable=False)
    raw_url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default="PENDING",
        nullable=False,
        index=True,
    )  # PENDING, ENRICHED, EVALUATED, FAILED, BLOCKED

    last_scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships (1:1 with Intelligence and Assessment, 1:N with Notifications)
    threat_intelligence: Mapped["ThreatIntelligence"] = relationship(
        "ThreatIntelligence",
        back_populates="url",
        uselist=False,
        cascade="all, delete-orphan",
    )
    threat_assessment: Mapped["ThreatAssessment"] = relationship(
        "ThreatAssessment",
        back_populates="url",
        uselist=False,
        cascade="all, delete-orphan",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification",
        back_populates="url",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ScannedUrl id={self.id} domain={self.domain} status={self.status}>"
