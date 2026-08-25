"""Media message moderation handler for photos, videos, video notes, and stickers.

Enforcement policy:
- Known spam pHash -> delete + ban.
- NSFW -> delete + warn + admin review card; auto-ban on repeat offense.
- Soft signals (QR/OCR) -> delete + admin review card only (no auto sanction).
- Oversized media (> MAX_ORIGINAL_SCAN_BYTES) is scanned via thumbnail with
  sanctions capped at delete + review card: no bans from a low-res preview.
"""

import io
from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.guards import enforce_source_guards
from bot.utils.notices import send_admin_review_card, send_group_moderation_notice
from bot.utils.sanctions import SanctionsExecutor
from core.logger import logger
from models import AuditLog, Chat, User
from services.ai.schema import SuggestedAction, ViolationCategory
from services.media.pipeline import MediaModerationPipeline
from services.moderation.night_mode import is_night_mode_active

router = Router(name="media_moderation")

# Files above this size are scanned through their thumbnail only; sanctions
# from such low-resolution evidence are capped to avoid wrongful bans.
MAX_ORIGINAL_SCAN_BYTES = 20 * 1024 * 1024


def _select_media_target(message: Message) -> tuple[str, object, bool]:
    """Pick (media_type, file_target, scan_is_low_res) for the incoming media."""
    if message.photo:
        return "photo", message.photo[-1], False
    if message.video:
        target = message.video
    elif message.video_note:
        target = message.video_note
    elif message.animation:
        target = message.animation
    elif message.sticker:
        target = message.sticker
    else:
        return "", None, False

    file_size = getattr(target, "file_size", None)
    thumbnail = getattr(target, "thumbnail", None)

    # Scan the original when its size is known and within limits; otherwise
    # fall back to the thumbnail with capped sanctions. When size is unknown,
    # scan the original (bots receive files up to 20 MB anyway).
    if thumbnail and file_size is not None and file_size > MAX_ORIGINAL_SCAN_BYTES:
        return "video_lowres" if (message.video or message.video_note) else "media_lowres", thumbnail, True
    return (
        "video" if message.video else "video_note" if message.video_note
        else "animation" if message.animation else "sticker"
    ), target, False


async def _count_prior_nsfw_offenses(session: AsyncSession, user_db: User) -> int:
    """Count previous confirmed NSFW detections for this user in this chat."""
    result = await session.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.user_id == user_db.id,
            AuditLog.category == ViolationCategory.ADULT_NSFW.value,
        )
    )
    return result.scalar() or 0


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

    # 2. Anti-channel / anti-inline-bot source guards (same policy as text path)
    if not await enforce_source_guards(message, chat_db):
        return

    user_db = await SanctionsExecutor.get_or_create_user(
        session=session,
        chat_id=chat_id,
        telegram_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    user_db.message_count += 1

    # 3. Determine media target and download into memory (no disk write)
    media_type, file_target, low_res_scan = _select_media_target(message)
    if not file_target:
        return

    try:
        buffer = io.BytesIO()
        await message.bot.download(file_target, destination=buffer)
        media_bytes = buffer.getvalue()
    except Exception as download_err:
        logger.warning(f"Failed to download media for inspection: {download_err}")
        return

    # 4. Run local media pipeline honoring per-chat scanner toggles
    verdict = await MediaModerationPipeline.process_media(
        media_bytes=media_bytes,
        media_type="photo" if media_type == "photo" else ("video" if "video" in media_type else "animation"),
        scan_nsfw=chat_db.media_nsfw_filter_enabled,
        scan_qr=chat_db.media_qr_filter_enabled,
        scan_ocr=chat_db.media_ocr_filter_enabled,
    )

    if not verdict.is_violation:
        return

    cat_key = verdict.category.value
    logger.info(
        f"Media violation detected in {chat_id} by user {user_id}: {cat_key} "
        f"({verdict.confidence}%, low_res={low_res_scan}, review={verdict.requires_admin_review})"
    )

    # Category disabled by admins -> pass entirely (parity with text path)
    if (chat_db.category_actions or {}).get(cat_key) == "ignore":
        logger.info(f"Category '{cat_key}' is set to IGNORE in chat {chat_id}. Media passed.")
        return

    user_name = message.from_user.full_name
    preview = f"[{str(media_type).upper()}] {verdict.reason}"

    # Night mode: delete and log for review, defer punitive sanctions
    # (known spam pHash fingerprints stay enforced — they are deterministic)
    if is_night_mode_active(chat_db) and verdict.category != ViolationCategory.ADULT_NSFW:
        logger.info(f"Night mode active in chat {chat_id}: media sanction deferred for user {user_id}")
        audit_entry = AuditLog(
            chat_id=chat_id,
            user_id=user_db.id,
            action_type="night_mode_review",
            category=cat_key,
            reason=f"[Ночной режим] {verdict.reason}",
            confidence=verdict.confidence,
            raw_message_snippet=preview[:400],
        )
        session.add(audit_entry)
        await session.flush()
        await send_admin_review_card(
            bot=message.bot, chat_db=chat_db, user_name=user_name, user_id=user_id,
            message_preview=preview, category=cat_key, confidence=verdict.confidence,
            reason=f"{verdict.reason} (ночной режим — санкция отложена)",
            audit_entry_id=audit_entry.id,
        )
        return

    # 5. Delete offending message in all enforcement paths
    await SanctionsExecutor.delete_message(message.bot, chat_id, message.message_id)

    action_title = "Удаление сообщения"

    if verdict.requires_admin_review or low_res_scan:
        # Soft signals & oversized-media previews: admin decides, no auto sanction
        audit_entry = AuditLog(
            chat_id=chat_id,
            user_id=user_db.id,
            action_type="review_required",
            category=cat_key,
            reason=f"[Admin Review] {verdict.reason}",
            confidence=verdict.confidence,
            raw_message_snippet=preview[:400],
        )
        session.add(audit_entry)
        await session.flush()

        await send_group_moderation_notice(
            bot=message.bot, chat_id=chat_id, user_name=user_name, user_id=user_id,
            action_title="Сообщение удалено, ожидает проверки администратора",
            category=cat_key, confidence=verdict.confidence, reason=verdict.reason,
            audit_entry_id=audit_entry.id,
        )
        await send_admin_review_card(
            bot=message.bot, chat_db=chat_db, user_name=user_name, user_id=user_id,
            message_preview=preview, category=cat_key, confidence=verdict.confidence,
            reason=verdict.reason, audit_entry_id=audit_entry.id,
        )
        return

    if verdict.category == ViolationCategory.ADULT_NSFW:
        prior_offenses = await _count_prior_nsfw_offenses(session, user_db)

        if prior_offenses >= 1:
            # Repeat offender: escalate to automatic ban
            await SanctionsExecutor.ban_user(
                message.bot, session, chat_id, user_db,
                reason=f"Повторная отправка неприемлемого контента: {verdict.reason}",
            )
            action_title = "Удаление + БАН (повторное срабатывание NSFW)"
            action_type = "ban_user"
            is_ban_action = True
        else:
            # First offense: delete + warn, admin confirms ban manually
            await SanctionsExecutor.apply_warn(
                bot=message.bot, session=session, chat_db=chat_db, user_db=user_db,
                reason=verdict.reason, category=cat_key, message_id=message.message_id,
            )
            action_title = "Удаление + Варн (NSFW, ожидает подтверждения админом)"
            action_type = "warn"
            is_ban_action = False
    elif verdict.suggested_action == SuggestedAction.BAN_USER:
        # Known spam pHash fingerprint
        await SanctionsExecutor.ban_user(message.bot, session, chat_id, user_db, reason=verdict.reason)
        action_title = "Удаление + БАН (известный спам-отпечаток)"
        action_type = "ban_user"
        is_ban_action = True
    else:
        await SanctionsExecutor.apply_warn(
            bot=message.bot, session=session, chat_db=chat_db, user_db=user_db,
            reason=verdict.reason, category=cat_key, message_id=message.message_id,
        )
        action_title = "Удаление + Варн"
        action_type = "warn"
        is_ban_action = False

    # 6. Record in Audit Logs
    audit_entry = AuditLog(
        chat_id=chat_id,
        user_id=user_db.id,
        action_type=action_type,
        category=cat_key,
        reason=verdict.reason,
        confidence=verdict.confidence,
        raw_message_snippet=preview[:400],
    )
    session.add(audit_entry)
    await session.flush()

    # 7. Group notice with appeal button + admin review card (parity with text path)
    await send_group_moderation_notice(
        bot=message.bot, chat_id=chat_id, user_name=user_name, user_id=user_id,
        action_title=action_title, category=cat_key, confidence=verdict.confidence,
        reason=verdict.reason, audit_entry_id=audit_entry.id,
    )
    await send_admin_review_card(
        bot=message.bot, chat_db=chat_db, user_name=user_name, user_id=user_id,
        message_preview=preview, category=cat_key, confidence=verdict.confidence,
        reason=verdict.reason, audit_entry_id=audit_entry.id, is_ban_action=is_ban_action,
    )
