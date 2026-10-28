"""
Telegram Chats and Messages domain models.
Stores monitored channels/groups metadata and ingested message headers.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.telegram_accounts.models import TelegramAccount


class TelegramChat(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Monitored Telegram chat or channel entity."""

    __tablename__ = "telegram_chats"

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("telegram_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )  # CHANNEL, SUPERGROUP, GROUP, PRIVATE
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    account: Mapped["TelegramAccount"] = relationship("TelegramAccount", back_populates="chats")
    messages: Mapped[list["TelegramMessage"]] = relationship(
        "TelegramMessage",
        back_populates="chat",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<TelegramChat id={self.id} title={self.title} type={self.type}>"


class TelegramMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Message header entity with URL indicators."""

    __tablename__ = "telegram_messages"

    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("telegram_chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    telegram_message_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    sender_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sender_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    has_urls: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    url_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    chat: Mapped["TelegramChat"] = relationship("TelegramChat", back_populates="messages")

    def __repr__(self) -> str:
        return f"<TelegramMessage id={self.id} msg_id={self.telegram_message_id} has_urls={self.has_urls}>"
