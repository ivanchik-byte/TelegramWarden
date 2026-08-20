"""Media message moderation handler for photos, videos, video notes, and stickers."""

import io
from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.sanctions import SanctionsExecutor
from core.logger import logger
from models import Chat, AuditLog
from services.ai.schema import SuggestedAction, ViolationCategory
from services.media.pipeline import MediaModerationPipeline

router = Router(name="media_moderation")


@router.message(F.photo | F.video | F.video_note | F.animation | F.sticker)
async def handle_media_message(message: Message, session: AsyncSession) -> None:
    """Download and process incoming media through the local CPU pipeline (0 tokens)."""
    chat_id = message.chat.id
    if chat_id > 0 or not message.from_user:
        return

    # 1. Load chat configuration
    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()
    if not chat_db or not chat_db.is_active:
        return

    user_id = message.from_user.id
    if user_id in (chat_db.whitelisted_users or []):
        return

    user_db = await SanctionsExecutor.get_or_create_user(
        session=session,
        chat_id=chat_id,
        telegram_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    user_db.message_count += 1

    # 2. Determine media type and target file object
    media_type = "photo"
    file_target = None

    if message.photo:
        media_type = "photo"
        file_target = message.photo[-1]
    elif message.video:
        media_type = "video"
        file_target = message.video.thumbnail or message.video
    elif message.video_note:
        media_type = "video_note"
        file_target = message.video_note.thumbnail or message.video_note
    elif message.animation:
        media_type = "animation"
        file_target = message.animation.thumbnail or message.animation
    elif message.sticker:
        media_type = "sticker"
        file_target = message.sticker.thumbnail or message.sticker

    if not file_target:
        return

    # 3. Stream download directly into memory buffer (no disk write)
    try:
        buffer = io.BytesIO()
        await message.bot.download(file_target, destination=buffer)
        media_bytes = buffer.getvalue()
    except Exception as download_err:
        logger.warning(f"Failed to download media for inspection: {download_err}")
        return

    # 4. Run local media moderation pipeline
    verdict = await MediaModerationPipeline.process_media(media_bytes=media_bytes, media_type=media_type)

    if not verdict.is_violation:
        return

    logger.info(f"Media violation detected in {chat_id} by user {user_id}: {verdict.category} ({verdict.confidence}%)")

    # 5. Delete offending message
    await SanctionsExecutor.delete_message(message.bot, chat_id, message.message_id)

    # 6. Enforce sanction
    if verdict.suggested_action == SuggestedAction.BAN_USER or verdict.category == ViolationCategory.ADULT_NSFW:
        await SanctionsExecutor.ban_user(message.bot, session, chat_id, user_db, reason=verdict.reason)
    else:
        await SanctionsExecutor.apply_warn(
            bot=message.bot,
            session=session,
            chat_db=chat_db,
            user_db=user_db,
            reason=verdict.reason,
            category=verdict.category.value,
            message_id=message.message_id,
        )

    # 7. Record in Audit Logs
    audit_entry = AuditLog(
        chat_id=chat_id,
        user_id=user_db.id,
        action_type=verdict.suggested_action.value,
        category=verdict.category.value,
        reason=verdict.reason,
        confidence=verdict.confidence,
        raw_message_snippet=f"[{media_type.upper()}] violation",
    )
    session.add(audit_entry)
