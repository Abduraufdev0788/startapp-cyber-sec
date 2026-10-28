"""
Threat Intelligence domain model.
Persists objective technical observations (WHOIS domain age, DNS, SSL, bounded HTTP response).
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.url_scanning.models import ScannedUrl


class ThreatIntelligence(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Technical enrichment evidence entity."""

    __tablename__ = "threat_intelligence"

    url_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scanned_urls.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    domain_age_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    registrar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dns_records: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    ssl_issuer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ssl_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    has_login_form: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_password_input: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    redirect_chain: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    text_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    url: Mapped["ScannedUrl"] = relationship("ScannedUrl", back_populates="threat_intelligence")

    def __repr__(self) -> str:
        return f"<ThreatIntelligence url_id={self.url_id} domain_age={self.domain_age_days}d status={self.http_status}>"
