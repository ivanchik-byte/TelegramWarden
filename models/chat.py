"""Chat configuration and per-group policy model."""

from typing import Optional, Any
from sqlalchemy import BigInteger, Boolean, Float, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base
from models.base import TimestampMixin


class Chat(Base, TimestampMixin):
    """Configuration and settings for a moderated Telegram Chat/Group."""

    __tablename__ = "chats"

    # Telegram Chat ID (can be negative, e.g. -1001234567890)
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="Telegram Group")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Admin Audit Log Channel/Topic
    log_channel_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # 1. Join & Gatekeeper Settings
    captcha_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    captcha_type: Mapped[str] = mapped_column(String(32), default="button")  # 'button', 'ai_profiling'
    captcha_timeout_seconds: Mapped[int] = mapped_column(Integer, default=120)
    cas_check_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    anti_raid_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    clean_service_messages: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 2. Protection & Restrictions
    allow_sender_chat: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # write as channel
    allow_via_bot: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)        # inline bots
    newbie_media_lock_hours: Mapped[int] = mapped_column(Integer, default=0)                # 0 = disabled

    # 3. AI & Moderation Engine
    ai_moderation_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ai_confidence_threshold: Mapped[float] = mapped_column(Float, default=85.0)             # >85% auto-punish
    ai_review_threshold: Mapped[float] = mapped_column(Float, default=50.0)                 # 50-85% review/warn
    ai_sampling_rate: Mapped[float] = mapped_column(Float, default=0.05)                    # 5% random sampling
    full_scan_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 100% full scan

    # 4. Media & Vision Protection (0 tokens on CPU)
    media_nsfw_filter_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    media_qr_filter_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    media_ocr_filter_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 5. Sanctions & Warnings
    warn_limit: Mapped[int] = mapped_column(Integer, default=3)
    warn_punishment: Mapped[str] = mapped_column(String(32), default="mute")  # 'mute', 'ban', 'kick'
    warn_mute_duration_minutes: Mapped[int] = mapped_column(Integer, default=1440)  # 24 hours

    # 6. Night Mode / Quiet Hours
    night_mode_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    night_mode_start: Mapped[str] = mapped_column(String(8), default="23:00")
    night_mode_end: Mapped[str] = mapped_column(String(8), default="08:00")
    night_mode_timezone: Mapped[str] = mapped_column(String(64), default="UTC")

    # 7. Advanced JSON Configurations (Whitelists, Topic Overrides)
    whitelisted_users: Mapped[list[int]] = mapped_column(JSON, default=list)
    whitelisted_channels: Mapped[list[int]] = mapped_column(JSON, default=list)
    whitelisted_bots: Mapped[list[str]] = mapped_column(JSON, default=list)
    topic_rules_override: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="chat", cascade="all, delete-orphan")
    warns: Mapped[list["Warn"]] = relationship("Warn", back_populates="chat", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="chat", cascade="all, delete-orphan")


# Forward references for typing
from models.user import User  # noqa: E402
from models.warn import Warn  # noqa: E402
from models.log import AuditLog  # noqa: E402
