"""
Threat Assessment domain model.
Persists synthesized risk evaluation, risk score (0-100), AI reasoning, and brand impersonation verdict.
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.url_scanning.models import ScannedUrl


class ThreatAssessment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Final phishing/scam evaluation entity."""

    __tablename__ = "threat_assessments"

    url_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scanned_urls.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    verdict: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
    )  # PHISHING, SCAM, SUSPICIOUS, BENIGN, UNKNOWN
    risk_score: Mapped[int] = mapped_column(Integer, index=True, nullable=False)  # 0 to 100
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0.0 to 1.0

    impersonated_brand: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reasons: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    gemini_response: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    evaluated_by: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )  # e.g., GEMINI_1_5_FLASH, HEURISTIC_FALLBACK

    # Relationships
    url: Mapped["ScannedUrl"] = relationship("ScannedUrl", back_populates="threat_assessment")

    def __repr__(self) -> str:
        return f"<ThreatAssessment url_id={self.url_id} verdict={self.verdict} score={self.risk_score}>"
