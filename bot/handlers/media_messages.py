"""Media message moderation handler for photos, videos, video notes, and stickers.

Enforcement policy:
- Known spam pHash -> delete + ban.
- NSFW -> delete + warn + admin review card; auto-ban on repeat offense.
- Soft signals (QR/OCR) -> delete + admin review card only (no auto sanction).
- Oversized media (> MAX_ORIGINAL_SCAN_BYTES) is scanned via thumbnail with
  sanctions capped at delete + review card: no bans from a low-res preview.
"""

import io
from datetime import datetime, timezone
from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.guards import enforce_source_guards
from bot.utils.notices import send_admin_review_card, send_group_moderation_notice
from bot.utils.sanctions import SanctionsExecutor
from bot.utils.text_moderation import moderate_text_content
from core.logger import logger
from models import AuditLog, Chat, User
from services.ai.schema import SuggestedAction, ViolationCategory
from services.media.pipeline import MediaModerationPipeline, sniff_media_kind
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
            AuditLog.chat_id == user_db.chat_id,
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

    # 3. Newbie media lock: newcomers cannot post media for N hours
    lock_hours = chat_db.newbie_media_lock_hours or 0
    if lock_hours > 0:
        age_hours = (datetime.now(timezone.utc) - user_db.first_seen_at).total_seconds() / 3600
        if age_hours < lock_hours:
            logger.info(f"Newbie media lock active in {chat_id}: media from user {user_id} deleted ({age_hours:.1f}h < {lock_hours}h)")
            await SanctionsExecutor.delete_message(message.bot, chat_id, message.message_id)
            try:
                await message.bot.send_message(
                    chat_id=chat_id,
                    text=f"{message.from_user.first_name}, отправка медиафайлов доступна через "
                         f"{lock_hours} часов после входа в чат.",
                )
            except Exception as notify_err:
                logger.debug(f"Failed to send newbie lock notice: {notify_err}")
            return

    # 4. Determine media target and download into memory (no disk write)
    # Animated TGS (Lottie) stickers cannot be decoded by any local scanner:
    # they must not silently pass — delete and hand to admin review.
    if message.sticker and getattr(message.sticker, "is_animated", False):
        logger.info(f"Animated TGS sticker from {user_id} in {chat_id} — unscannable, held for review")
        await SanctionsExecutor.delete_message(message.bot, chat_id, message.message_id)
        audit_entry = AuditLog(
            chat_id=chat_id,
            user_id=user_db.id,
            action_type="review_required",
            category=ViolationCategory.ADULT_NSFW.value,
            reason="[TGS] Анимированный стикер не поддается локальному скану — проверьте вручную",
            confidence=0.0,
            raw_message_snippet="[TGS STICKER]",
        )
        session.add(audit_entry)
        await session.flush()
        await send_admin_review_card(
            bot=message.bot, chat_db=chat_db, user_name=message.from_user.full_name, user_id=user_id,
            message_preview="[TGS STICKER]", category="adult_nsfw",
            confidence=0.0, reason="Анимированный стикер удалён: локальный скан недоступен",
            audit_entry_id=audit_entry.id,
        )
        return

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

    # 4. Caption text follows the exact same moderation policy as plain text
    caption_text = message.caption or ""
    if caption_text:
        handled = await moderate_text_content(
            bot=message.bot,
            session=session,
            message=message,
            chat_db=chat_db,
            user_db=user_db,
            raw_text=caption_text,
        )
        if handled:
            return  # caption violation already sanctioned; media inspected separately

    # 5. Run local media pipeline honoring per-chat scanner toggles.
    # Animations (MP4/GIF) and video stickers (webm) need keyframe sampling,
    # otherwise PIL cannot decode them and they would silently bypass the scan.
    is_motion_media = bool(
        message.video or message.video_note or message.animation
        or (message.sticker and getattr(message.sticker, "is_video", False))
    )
    # Oversized videos are inspected via their JPEG thumbnail: that is a still
    # image, not a container, so it must be decoded with the image path.
    scan_kind = "video" if (is_motion_media and not low_res_scan) else "photo"
    verdict = await MediaModerationPipeline.process_media(
        media_bytes=media_bytes,
        media_type=scan_kind,
        scan_nsfw=chat_db.media_nsfw_filter_enabled,
        scan_qr=chat_db.media_qr_filter_enabled,
        scan_ocr=chat_db.media_ocr_filter_enabled,
    )

    if not verdict.is_violation:
        # Fail-closed for newcomers: when NSFW could not actually run (model
        # missing, inference failure) their unscanable media is held for admin
        # review instead of silently passing. Newcomers are the primary
        # source of porn raids; the cost of a false hold is one admin click.
        is_newcomer = user_db.message_count < 5 or (
            (datetime.now(timezone.utc) - user_db.first_seen_at).days < 3
        )
        if is_newcomer and not low_res_scan and not verdict.nsfw_checked:
            logger.warning(f"NSFW scan unavailable for newcomer media in {chat_id}, user {user_id} — holding for review")
            await SanctionsExecutor.delete_message(message.bot, chat_id, message.message_id)
            audit_entry = AuditLog(
                chat_id=chat_id,
                user_id=user_db.id,
                action_type="review_required",
                category=ViolationCategory.ADULT_NSFW.value,
                reason="[Fail-closed] Медиа новичка не удалось просканировать — проверьте вручную",
                confidence=0.0,
                raw_message_snippet=f"[{str(media_type).upper()}] unscanned",
            )
            session.add(audit_entry)
            await session.flush()
            await send_admin_review_card(
                bot=message.bot, chat_db=chat_db, user_name=message.from_user.full_name, user_id=user_id,
                message_preview=f"[{media_type}] NSFW-скан недоступен", category="adult_nsfw",
                confidence=0.0, reason="Медиа новичка удалено: сканер был недоступен",
                audit_entry_id=audit_entry.id,
            )
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

    # Night mode: defer ONLY soft admin-review signals (QR/OCR). Deterministic
    # evidence — NSFW detections and known-spam pHash fingerprints — stays
    # enforced around the clock, matching the policy comment below.
    if is_night_mode_active(chat_db) and verdict.requires_admin_review:
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


@router.message(F.document)
async def handle_document_message(message: Message, session: AsyncSession) -> None:
    """Moderate file attachments: caption text plus embedded image/video content.

    Documents were previously unmoderated entirely, letting NSFW media through
    as a plain file. Scannable payloads (images/video) go through the same
    local pipeline; everything else is checked by caption and metadata only.
    """
    chat_id = message.chat.id
    if chat_id > 0 or not message.from_user:
        return

    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()
    if not chat_db or not chat_db.is_active:
        return

    user_id = message.from_user.id
    if user_id in (chat_db.whitelisted_users or []):
        return

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

    document = message.document
    mime = (document.mime_type or "").lower()
    file_size = document.file_size or 0

    # Caption moderation first — identical policy to the plain-text path
    if message.caption:
        handled = await moderate_text_content(
            bot=message.bot,
            session=session,
            message=message,
            chat_db=chat_db,
            user_db=user_db,
            raw_text=message.caption,
        )
        if handled:
            return

    # Download first, then trust the bytes — declared MIME is attacker-
    # controlled (application/octet-stream is a classic NSFW disguise)
    if file_size > MAX_ORIGINAL_SCAN_BYTES:
        # Oversized files cannot be scanned locally; they are NOT deleted
        # (legit archives exist) but admins must see them, not silence.
        logger.info(f"Oversized document {document.file_name!r} ({file_size} bytes) in {chat_id} — flagged for review")
        audit_entry = AuditLog(
            chat_id=chat_id,
            user_id=user_db.id,
            action_type="review_required",
            category=ViolationCategory.OTHER_VIOLATION.value,
            reason=f"[Документ >{MAX_ORIGINAL_SCAN_BYTES // (1024*1024)}МБ] Файл превышает лимит сканирования",
            confidence=0.0,
            raw_message_snippet=f"[DOCUMENT {(document.file_name or '')[:60]}]",
        )
        session.add(audit_entry)
        await session.flush()
        await send_admin_review_card(
            bot=message.bot, chat_db=chat_db, user_name=message.from_user.full_name, user_id=user_id,
            message_preview=f"[DOCUMENT {(document.file_name or '')[:60]}] {file_size} bytes",
            category=ViolationCategory.OTHER_VIOLATION.value, confidence=0.0,
            reason="Крупный файл не поддается локальному сканированию — проверьте вручную",
            audit_entry_id=audit_entry.id,
        )
        return

    try:
        buffer = io.BytesIO()
        await message.bot.download(document, destination=buffer)
        media_bytes = buffer.getvalue()
    except Exception as download_err:
        logger.warning(f"Failed to download document for inspection: {download_err}")
        return

    # Magic bytes decide; declared MIME is only a fallback hint
    sniffed = sniff_media_kind(media_bytes)
    if sniffed is None and mime:
        sniffed = {"image": "photo", "video": "video"}.get(mime.split("/")[0])
    if sniffed not in ("photo", "video", "animation"):
        return  # genuinely not scannable visual content

    verdict = await MediaModerationPipeline.process_media(
        media_bytes=media_bytes,
        media_type="video" if sniffed in ("video", "animation") else "photo",
        scan_nsfw=chat_db.media_nsfw_filter_enabled,
        scan_qr=chat_db.media_qr_filter_enabled,
        scan_ocr=chat_db.media_ocr_filter_enabled,
    )

    if not verdict.is_violation:
        return

    logger.info(f"Document violation detected in {chat_id} by user {user_id}: {verdict.category}")
    cat_key = verdict.category.value

    await SanctionsExecutor.delete_message(message.bot, chat_id, message.message_id)

    # Documents are an evasion channel: NSFW evidence here escalates straight
    # to admin review with a ban button rather than auto-ban.
    audit_entry = AuditLog(
        chat_id=chat_id,
        user_id=user_db.id,
        action_type="review_required",
        category=cat_key,
        reason=f"[Документ] {verdict.reason}",
        confidence=verdict.confidence,
        raw_message_snippet=f"[DOCUMENT {(document.file_name or '')[:60]}]",
    )
    session.add(audit_entry)
    await session.flush()

    await send_group_moderation_notice(
        bot=message.bot, chat_id=chat_id, user_name=message.from_user.full_name, user_id=user_id,
        action_title="Файл удалён, ожидает проверки администратора",
        category=cat_key, confidence=verdict.confidence, reason=verdict.reason,
        audit_entry_id=audit_entry.id,
    )
    await send_admin_review_card(
        bot=message.bot, chat_db=chat_db, user_name=message.from_user.full_name, user_id=user_id,
        message_preview=f"[{mime}] {verdict.reason}", category=cat_key,
        confidence=verdict.confidence, reason=verdict.reason, audit_entry_id=audit_entry.id,
    )
