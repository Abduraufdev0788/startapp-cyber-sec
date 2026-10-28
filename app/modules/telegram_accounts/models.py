"""
Telegram Account domain model.
Persists connected Telegram user accounts with AES-256-GCM encrypted Telethon sessions.
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.telegram_chats.models import TelegramChat
    from app.modules.users.models import User


class TelegramAccount(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Connected Telegram user account entity."""

    __tablename__ = "telegram_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    phone_number_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # Highly sensitive: AES-256-GCM encrypted Telethon session binary envelope
    encrypted_session: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    status: Mapped[str] = mapped_column(
        String(32),
        default="CONNECTED",
        nullable=False,
        index=True,
    )  # CONNECTED, DISCONNECTED, REVOKED, ERROR
    auth_state: Mapped[str] = mapped_column(
        String(32),
        default="AUTHORIZED",
        nullable=False,
    )  # AUTHORIZED, NEED_CODE, NEED_PASSWORD

    last_connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="telegram_accounts")
    chats: Mapped[list["TelegramChat"]] = relationship(
        "TelegramChat",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<TelegramAccount id={self.id} tg_uid={self.telegram_user_id} status={self.status}>"
