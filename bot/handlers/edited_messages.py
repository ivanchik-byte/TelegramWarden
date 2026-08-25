"""Edited message handler protecting against stealth edit spam attacks.

Reuses the shared moderation core so edits follow the exact same policy
as fresh messages: review thresholds, moderation modes, category actions,
night mode and tiered sanctions — with an "edited" marker on every reason.
"""

from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.sanctions import SanctionsExecutor
from bot.utils.text_moderation import extract_entity_urls, moderate_text_content
from core.logger import logger
from models import Chat
from services.ai.normalizer import TextSanitizer
from services.ai.risk_scorer import RiskScorer

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
    # Hidden-entity links count exactly like visible ones
    for url in extract_entity_urls(message):
        if url not in sanitized.extracted_urls:
            sanitized.extracted_urls.append(url)

    # Same 0-token heuristic gate as normal sends: an edit turning clean text
    # into a toxic offer without links must still reach the LLM.
    days_in_chat = (datetime.now(timezone.utc) - user_db.first_seen_at).days
    risk_result = RiskScorer.evaluate(
        sanitized=sanitized,
        user_message_count=user_db.message_count,
        user_days_in_chat=days_in_chat,
        is_forward=False,
        sampling_rate=chat_db.ai_sampling_rate,
        telegram_id=user_id,
    )

    triggered = bool(
        sanitized.extracted_urls or sanitized.extracted_usernames
        or sanitized.had_invisible_characters or risk_result.should_call_ai
    )
    if not triggered:
        return

    logger.info(
        f"Edited message inspection in chat {chat_id} by {user_id}: "
        f"urls={len(sanitized.extracted_urls)}, risk={risk_result.risk_score}"
    )
    await moderate_text_content(
        bot=message.bot,
        session=session,
        message=message,
        chat_db=chat_db,
        user_db=user_db,
        raw_text=message.text or message.caption or "",
        source_label="Спам через редактирование: ",
    )
