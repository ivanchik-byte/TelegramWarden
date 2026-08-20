"""User reputation, history, and status model (Permanent Data Layer)."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base
from models.base import TimestampMixin


class User(Base, TimestampMixin):
    """Permanent user record within a specific moderated group."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("chats.chat_id", ondelete="CASCADE"), index=True, nullable=False)

    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), default="")
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Reputation & Trust
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    reputation_score: Mapped[int] = mapped_column(Integer, default=100)  # Starts at 100, drops with violations
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    total_violations_count: Mapped[int] = mapped_column(Integer, default=0)

    # Sanction States
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ban_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    banned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_muted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    muted_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Captcha verification status
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    chat: Mapped["Chat"] = relationship("Chat", back_populates="users")
    warns: Mapped[list["Warn"]] = relationship("Warn", back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")


# Forward references for typing
from models.chat import Chat  # noqa: E402
from models.warn import Warn  # noqa: E402
from models.log import AuditLog  # noqa: E402
