"""Edited message handler protecting against stealth edit spam attacks."""

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.notices import send_admin_review_card
from bot.utils.sanctions import SanctionsExecutor
from core.logger import logger
from models import AuditLog, Chat
from services.ai.client import ai_dispatcher
from services.ai.normalizer import TextSanitizer
from services.ai.schema import SuggestedAction
from services.moderation.night_mode import is_night_mode_active

router = Router(name="edited_messages")


@router.edited_message(F.text | F.caption)
async def handle_edited_message(message: Message, session: AsyncSession) -> None:
    """Re-inspect edited text messages and media captions to detect malicious substitutions."""
    chat_id = message.chat.id
    if chat_id > 0 or not message.from_user:
        return

    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()
    if not chat_db or not chat_db.is_active or not chat_db.ai_moderation_enabled:
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

    # Sanitize edited text (message body or media caption)
    sanitized = TextSanitizer.sanitize(message.text or message.caption or "")

    # If edited message now contains links or suspicious text -> inspect immediately
    if not (sanitized.extracted_urls or sanitized.extracted_usernames or sanitized.had_invisible_characters):
        return

    logger.info(f"Edited message contains new links/triggers in chat {chat_id}. Inspecting via AI...")
    verdict = await ai_dispatcher.analyze_message(
        message_text=sanitized.clean_text,
        user_info=f"Edited message by User {user_id}",
    )

    if not verdict.is_violation:
        return

    cat_key = verdict.category.value
    # Category disabled by admins -> pass (parity with the main moderation path)
    if (chat_db.category_actions or {}).get(cat_key) == "ignore":
        logger.info(f"Category '{cat_key}' is set to IGNORE in chat {chat_id}. Edited message passed.")
        return

    if verdict.confidence < (chat_db.ai_confidence_threshold or 85.0):
        return

    preview = sanitized.clean_text[:400]
    reason = f"Спам через редактирование: {verdict.reason}"

    await SanctionsExecutor.delete_message(message.bot, chat_id, message.message_id)

    # Night mode: defer punitive sanctions, keep delete + review card
    if is_night_mode_active(chat_db) and verdict.category.value != "illegal_contraband":
        action_type = "night_mode_review"
        reason = f"[Ночной режим] {reason}"
    elif verdict.suggested_action == SuggestedAction.BAN_USER:
        await SanctionsExecutor.ban_user(message.bot, session, chat_id, user_db, reason=reason)
        action_type = "ban_user"
    else:
        await SanctionsExecutor.apply_warn(
            bot=message.bot,
            session=session,
            chat_db=chat_db,
            user_db=user_db,
            reason=reason,
            category=cat_key,
            message_id=message.message_id,
        )
        action_type = "warn"

    audit_entry = AuditLog(
        chat_id=chat_id,
        user_id=user_db.id,
        action_type=action_type,
        category=cat_key,
        reason=f"Edit attack: {verdict.reason}",
        confidence=verdict.confidence,
        raw_message_snippet=preview,
    )
    session.add(audit_entry)
    await session.flush()

    if chat_db.send_suspicious_to_admin:
        await send_admin_review_card(
            bot=message.bot,
            chat_db=chat_db,
            user_name=message.from_user.full_name,
            user_id=user_id,
            message_preview=sanitized.clean_text,
            category=cat_key,
            confidence=verdict.confidence,
            reason=f"{verdict.reason} (обнаружено при редактировании сообщения)",
            audit_entry_id=audit_entry.id,
            is_ban_action=(action_type == "ban_user"),
        )
