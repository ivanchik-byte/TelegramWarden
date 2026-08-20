"""Warning history and expiration tracking model."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base
from core.config import settings
from models.base import TimestampMixin


class Warn(Base, TimestampMixin):
    """Warning issued to a user in a specific chat."""

    __tablename__ = "warns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chats.chat_id", ondelete="CASCADE"), index=True, nullable=False)

    reason: Mapped[str] = mapped_column(String(255), default="Community rules violation")
    category: Mapped[str] = mapped_column(String(64), default="general")  # 'spam', 'ad', 'toxic', 'nsfw', 'flood'
    message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Automatic expiration tracking (e.g. 14 days)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(days=settings.WARN_EXPIRATION_DAYS),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="warns")
    user: Mapped["User"] = relationship("User", back_populates="warns")


# Forward references for typing
from models.chat import Chat  # noqa: E402
from models.user import User  # noqa: E402
