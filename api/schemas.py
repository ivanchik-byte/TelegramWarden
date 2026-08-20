"""Pydantic schemas for FastAPI REST API and Telegram Mini App."""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class ChatListItemSchema(BaseModel):
    """Minimal chat info for the group selector."""

    chat_id: int
    title: str
    is_active: bool


class ChatSettingsResponseSchema(BaseModel):
    """Schema representing current chat configuration."""

    chat_id: int
    title: str
    is_active: bool
    captcha_enabled: bool
    captcha_type: str
    captcha_timeout_seconds: int
    cas_check_enabled: bool
    anti_raid_enabled: bool
    clean_service_messages: bool
    allow_sender_chat: bool
    allow_via_bot: bool
    newbie_media_lock_hours: int
    ai_moderation_enabled: bool
    moderation_mode: str
    send_suspicious_to_admin: bool
    category_actions: dict[str, str] = {}
    ai_confidence_threshold: float
    ai_review_threshold: float
    ai_sampling_rate: float
    full_scan_enabled: bool
    media_nsfw_filter_enabled: bool
    media_qr_filter_enabled: bool
    media_ocr_filter_enabled: bool
    warn_limit: int
    warn_punishment: str
    warn_mute_duration_minutes: int
    night_mode_enabled: bool
    night_mode_start: str
    night_mode_end: str
    night_mode_timezone: str
    whitelisted_users: list[int]
    whitelisted_channels: list[int]
    whitelisted_bots: list[str]


class ChatSettingsUpdateSchema(BaseModel):
    """Schema for partial updates to chat settings."""

    is_active: Optional[bool] = None
    captcha_enabled: Optional[bool] = None
    captcha_type: Optional[str] = None
    captcha_timeout_seconds: Optional[int] = None
    cas_check_enabled: Optional[bool] = None
    anti_raid_enabled: Optional[bool] = None
    clean_service_messages: Optional[bool] = None
    allow_sender_chat: Optional[bool] = None
    allow_via_bot: Optional[bool] = None
    newbie_media_lock_hours: Optional[int] = None
    ai_moderation_enabled: Optional[bool] = None
    moderation_mode: Optional[str] = None
    send_suspicious_to_admin: Optional[bool] = None
    category_actions: Optional[dict[str, str]] = None
    ai_confidence_threshold: Optional[float] = Field(None, ge=50.0, le=99.0)
    ai_review_threshold: Optional[float] = Field(None, ge=20.0, le=85.0)
    ai_sampling_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    full_scan_enabled: Optional[bool] = None
    media_nsfw_filter_enabled: Optional[bool] = None
    media_qr_filter_enabled: Optional[bool] = None
    media_ocr_filter_enabled: Optional[bool] = None
    warn_limit: Optional[int] = Field(None, ge=1, le=10)
    warn_punishment: Optional[str] = None
    warn_mute_duration_minutes: Optional[int] = None
    night_mode_enabled: Optional[bool] = None
    night_mode_start: Optional[str] = None
    night_mode_end: Optional[str] = None
    night_mode_timezone: Optional[str] = None
    whitelisted_users: Optional[list[int]] = None
    whitelisted_channels: Optional[list[int]] = None
    whitelisted_bots: Optional[list[str]] = None


class CategoryStatItem(BaseModel):
    """Category statistics item."""

    category: str
    count: int


class ChatStatsResponseSchema(BaseModel):
    """Aggregated moderation statistics schema."""

    chat_id: int
    total_violations: int
    total_warns_issued: int
    total_bans: int
    total_mutes: int
    false_positives_count: int
    violations_by_category: list[CategoryStatItem]


class AuditLogItemSchema(BaseModel):
    """Individual audit log entry for dashboard table."""

    id: int
    user_id: Optional[int]
    action_type: str
    category: str
    reason: str
    confidence: Optional[float]
    raw_message_snippet: Optional[str]
    created_at: datetime
    is_false_positive: bool
