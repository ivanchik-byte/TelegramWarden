"""API routes for managing group moderation settings."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.auth import TelegramUser, get_current_telegram_user
from api.schemas import ChatListItemSchema, ChatSettingsResponseSchema, ChatSettingsUpdateSchema
from core.config import settings
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
        ai_confidence_threshold=chat_db.ai_confidence_threshold,
        ai_sampling_rate=chat_db.ai_sampling_rate,
        media_nsfw_filter_enabled=chat_db.media_nsfw_filter_enabled,
        media_qr_filter_enabled=chat_db.media_qr_filter_enabled,
        media_ocr_filter_enabled=chat_db.media_ocr_filter_enabled,
        warn_limit=chat_db.warn_limit,
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
    result = await session.execute(select(Chat).order_by(Chat.title))
    all_chats = result.scalars().all()

    is_super = user.id in settings.superadmin_id_list
    accessible = []
    for chat in all_chats:
        wl = chat.whitelisted_users or []
        if is_super or user.id in wl:
            accessible.append(
                ChatListItemSchema(
                    chat_id=chat.chat_id,
                    title=chat.title,
                    is_active=chat.is_active,
                )
            )
    return accessible


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

    is_super = user.id in settings.superadmin_id_list
    is_whitelisted = user.id in (chat_db.whitelisted_users or [])
    if not (is_super or is_whitelisted):
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

    is_super = user.id in settings.superadmin_id_list
    is_whitelisted = user.id in (chat_db.whitelisted_users or [])
    if not (is_super or is_whitelisted):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not have permission to manage this chat",
        )

    # Apply partial updates
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(chat_db, field, value)

    await session.commit()
    await session.refresh(chat_db)

    return _chat_to_response(chat_db)
