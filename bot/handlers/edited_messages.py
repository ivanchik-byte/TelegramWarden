"""Edited message handler protecting against stealth edit spam attacks."""

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.sanctions import SanctionsExecutor
from core.logger import logger
from models import Chat, AuditLog
from services.ai.client import ai_dispatcher
from services.ai.normalizer import TextSanitizer
from services.ai.schema import SuggestedAction

router = Router(name="edited_messages")


@router.edited_message(F.text)
async def handle_edited_message(message: Message, session: AsyncSession) -> None:
    """Re-inspect edited text messages to detect malicious link or scam substitutions."""
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

    # Sanitize edited text
    sanitized = TextSanitizer.sanitize(message.text or "")

    # If edited message now contains links or suspicious text -> inspect immediately
    if sanitized.extracted_urls or sanitized.extracted_usernames or sanitized.had_invisible_characters:
        logger.info(f"Edited message contains new links/triggers in chat {chat_id}. Inspecting via AI...")
        verdict = await ai_dispatcher.analyze_message(
            message_text=sanitized.clean_text,
            user_info=f"Edited message by User {user_id}",
        )

        if verdict.is_violation and verdict.confidence >= chat_db.ai_confidence_threshold:
            logger.warning(f"Malicious edit detected in chat {chat_id} by {user_id}: {verdict.category}")
            await SanctionsExecutor.delete_message(message.bot, chat_id, message.message_id)

            if verdict.suggested_action == SuggestedAction.BAN_USER:
                await SanctionsExecutor.ban_user(message.bot, session, chat_id, user_db, reason=f"Спам через редактирование: {verdict.reason}")
            else:
                await SanctionsExecutor.apply_warn(
                    bot=message.bot,
                    session=session,
                    chat_db=chat_db,
                    user_db=user_db,
                    reason=f"Спам через редактирование: {verdict.reason}",
                    category=verdict.category.value,
                    message_id=message.message_id,
                )

            audit_entry = AuditLog(
                chat_id=chat_id,
                user_id=user_db.id,
                action_type="edit_violation",
                category=verdict.category.value,
                reason=f"Edit attack: {verdict.reason}",
                confidence=verdict.confidence,
                raw_message_snippet=sanitized.clean_text[:400],
            )
            session.add(audit_entry)
