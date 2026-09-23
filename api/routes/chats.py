"""API routes for managing group moderation settings."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.auth import TelegramUser, get_current_telegram_user
from api.deps import can_access_chat, is_superadmin
from api.schemas import ChatListItemSchema, ChatSettingsResponseSchema, ChatSettingsUpdateSchema
from core.database import get_db_session
from models import Chat

router = APIRouter(prefix="/chats", tags=["Chats"])


def _chat_to_response(chat_db: Chat) -> ChatSettingsResponseSchema:
    """Map a Chat ORM object to its API response schema."""
    return ChatSettingsResponseSchema(
        chat_id=chat_db.chat_id,
        title=chat_db.title,
        is_active=chat_db.is_active,
        captcha_enabled=chat_db.captcha_enabled,
        captcha_type=chat_db.captcha_type,
        captcha_timeout_seconds=chat_db.captcha_timeout_seconds,
        cas_check_enabled=chat_db.cas_check_enabled,
        anti_raid_enabled=chat_db.anti_raid_enabled,
        clean_service_messages=chat_db.clean_service_messages,
        allow_sender_chat=chat_db.allow_sender_chat,
        allow_via_bot=chat_db.allow_via_bot,
        newbie_media_lock_hours=chat_db.newbie_media_lock_hours,
        ai_moderation_enabled=chat_db.ai_moderation_enabled,
        moderation_mode=getattr(chat_db, 'moderation_mode', 'ai_judge') or 'ai_judge',
        report_mode=getattr(chat_db, 'report_mode', 'admin_only'),
        send_suspicious_to_admin=getattr(chat_db, 'send_suspicious_to_admin', True),
        category_actions=getattr(chat_db, 'category_actions', {}) or {},
        ai_confidence_threshold=chat_db.ai_confidence_threshold,
        ai_review_threshold=getattr(chat_db, 'ai_review_threshold', 50.0),
        ai_sampling_rate=chat_db.ai_sampling_rate,
        full_scan_enabled=getattr(chat_db, 'full_scan_enabled', False),
        media_nsfw_filter_enabled=chat_db.media_nsfw_filter_enabled,
        media_qr_filter_enabled=chat_db.media_qr_filter_enabled,
        media_ocr_filter_enabled=chat_db.media_ocr_filter_enabled,
        warn_limit=chat_db.warn_limit,
        warn_expiration_days=getattr(chat_db, 'warn_expiration_days', 7) or 7,
        warn_punishment=chat_db.warn_punishment,
        warn_mute_duration_minutes=chat_db.warn_mute_duration_minutes,
        night_mode_enabled=chat_db.night_mode_enabled,
        night_mode_start=chat_db.night_mode_start,
        night_mode_end=chat_db.night_mode_end,
        night_mode_timezone=chat_db.night_mode_timezone,
        whitelisted_users=chat_db.whitelisted_users or [],
        whitelisted_channels=chat_db.whitelisted_channels or [],
        whitelisted_bots=chat_db.whitelisted_bots or [],
    )


@router.get("", response_model=list[ChatListItemSchema])
async def list_user_chats(
    user: TelegramUser = Depends(get_current_telegram_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ChatListItemSchema]:
    """Return all chats accessible to the authenticated user."""
    result = await session.execute(select(Chat).order_by(Chat.title).limit(500))
    all_chats = result.scalars().all()

    return [
        ChatListItemSchema(
            chat_id=chat.chat_id,
            title=chat.title,
            is_active=chat.is_active,
        )
        for chat in all_chats
        if can_access_chat(user.id, chat.whitelisted_users)
    ]


@router.get("/{chat_id}", response_model=ChatSettingsResponseSchema)
async def get_chat_settings(
    chat_id: int,
    user: TelegramUser = Depends(get_current_telegram_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChatSettingsResponseSchema:
    """Retrieve current security and moderation settings for a group."""
    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()

    if not chat_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found in database",
        )

    if not can_access_chat(user.id, chat_db.whitelisted_users):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not have permission to view this chat",
        )

    return _chat_to_response(chat_db)


@router.patch("/{chat_id}", response_model=ChatSettingsResponseSchema)
async def update_chat_settings(
    chat_id: int,
    payload: ChatSettingsUpdateSchema,
    user: TelegramUser = Depends(get_current_telegram_user),
    session: AsyncSession = Depends(get_db_session),
) -> ChatSettingsResponseSchema:
    """Update settings for a specific chat."""
    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()

    if not chat_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found",
        )

    if not can_access_chat(user.id, chat_db.whitelisted_users):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not have permission to manage this chat",
        )

    # Apply partial updates
    update_data = payload.model_dump(exclude_unset=True)

    # Privilege and safety-critical fields may only be managed by global
    # superadmins: a whitelisted member must neither extend their own access
    # nor switch off the bot's core defenses
    privileged_fields = {"whitelisted_users", "whitelisted_channels", "whitelisted_bots"}
    defense_fields = {
        "ai_moderation_enabled", "captcha_enabled", "anti_raid_enabled",
        "cas_check_enabled", "is_active", "full_scan_enabled",
        "media_nsfw_filter_enabled", "media_qr_filter_enabled",
        "media_ocr_filter_enabled",
    }
    forbidden = (privileged_fields | defense_fields).intersection(update_data)
    if not is_superadmin(user.id) and forbidden:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only superadmins may modify: {', '.join(sorted(forbidden))}",
        )

    for field, value in update_data.items():
        setattr(chat_db, field, value)

    await session.commit()
    await session.refresh(chat_db)

    return _chat_to_response(chat_db)
