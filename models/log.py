"""Moderation audit logs and admin action tracking model (Rotational Data Layer)."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base
from models.base import TimestampMixin


class AuditLog(Base, TimestampMixin):
    """Audit log entry for every moderation action (rotated after 30 days)."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chats.chat_id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)

    action_type: Mapped[str] = mapped_column(String(64), nullable=False)  # 'delete', 'warn', 'mute', 'ban', 'kick', 'captcha_kick'
    category: Mapped[str] = mapped_column(String(64), default="spam")     # 'crypto_scam', 'nsfw', 'ad', 'toxic', 'flood', 'cas'
    reason: Mapped[str] = mapped_column(String(500), default="")
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Message Snippet & Media Evidence
    raw_message_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Telegram file_id of stop-frame/photo

    # False Positive & Admin Feedback
    is_false_positive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    reviewed_by_admin_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    admin_action_taken: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # 'unbanned', 'unmuted', 'warn_removed'

    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="audit_logs")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")


# Forward references for typing
from models.chat import Chat  # noqa: E402
from models.user import User  # noqa: E402
