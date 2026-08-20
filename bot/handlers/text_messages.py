"""Message moderation handler for text, forwards, channels, and inline bots."""

from datetime import datetime, timezone
from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.sanctions import SanctionsExecutor
from core.logger import logger
from models import Chat, AuditLog
from services.ai.client import ai_dispatcher
from services.ai.normalizer import TextSanitizer
from services.ai.risk_scorer import RiskScorer
from services.ai.schema import SuggestedAction, ViolationCategory

router = Router(name="text_moderation")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_message(message: Message, session: AsyncSession) -> None:
    """Analyze incoming text message against security policies and AI intent engine."""
    chat_id = message.chat.id
    if chat_id > 0:  # Skip private bot chats
        return

    # 1. Load or initialize chat configuration
    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()
    if not chat_db:
        chat_db = Chat(chat_id=chat_id, title=message.chat.title or "Group")
        session.add(chat_db)
        await session.flush()

    if not chat_db.is_active:
        return

    # 2. Anti-Channel protection (Send as channel)
    if message.sender_chat:
        sender_channel_id = message.sender_chat.id
        if sender_channel_id != chat_id and not chat_db.allow_sender_chat:
            if sender_channel_id not in (chat_db.whitelisted_channels or []):
                logger.info(f"Unauthorized sender_chat {sender_channel_id} in group {chat_id}. Deleting.")
                await SanctionsExecutor.delete_message(message.bot, chat_id, message.message_id)
                try:
                    await message.bot.ban_chat_sender_chat(chat_id=chat_id, sender_chat_id=sender_channel_id)
                except Exception:
                    pass
                return

    if not message.from_user:
        return

    user_id = message.from_user.id
    if user_id in (chat_db.whitelisted_users or []):
        return  # Whitelisted user bypass

    # 3. Anti-Inline bot protection (via_bot)
    if message.via_bot and not chat_db.allow_via_bot:
        bot_username = f"@{message.via_bot.username}" if message.via_bot.username else ""
        if bot_username not in (chat_db.whitelisted_bots or []):
            logger.info(f"Unauthorized via_bot {bot_username} in {chat_id}. Deleting.")
            await SanctionsExecutor.delete_message(message.bot, chat_id, message.message_id)
            return

    # 4. Get or create permanent user profile
    user_db = await SanctionsExecutor.get_or_create_user(
        session=session,
        chat_id=chat_id,
        telegram_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    user_db.message_count += 1

    # 5. Sanitize text (strip zero-width, normalize homoglyphs, extract hidden links)
    raw_text = message.text or ""
    sanitized = TextSanitizer.sanitize(raw_text)

    # 6. Evaluate Risk Score (0-token filter)
    days_in_chat = (datetime.now(timezone.utc) - user_db.first_seen_at).days
    is_forward = bool(message.forward_origin)

    risk_result = RiskScorer.evaluate(
        sanitized=sanitized,
        user_message_count=user_db.message_count,
        user_days_in_chat=days_in_chat,
        is_forward=is_forward,
        sampling_rate=chat_db.ai_sampling_rate,
    )

    if not risk_result.should_call_ai or not chat_db.ai_moderation_enabled:
        return  # 0 tokens spent, message is clean

    # 7. Query AI Intent Engine
    user_context = f"User {user_id}, msgs: {user_db.message_count}, days: {days_in_chat}, warns: {user_db.total_violations_count}"
    verdict = await ai_dispatcher.analyze_message(
        message_text=sanitized.clean_text,
        user_info=user_context,
    )

    if not verdict.is_violation:
        return

    # 8. Apply Sanctions if Confidence threshold is met
    if verdict.confidence >= chat_db.ai_confidence_threshold:
        logger.info(f"AI violation flagged in chat {chat_id} by user {user_id}: {verdict.category} ({verdict.confidence}%)")

        # Delete offending message
        await SanctionsExecutor.delete_message(message.bot, chat_id, message.message_id)

        # Enforce action
        if verdict.suggested_action == SuggestedAction.BAN_USER or verdict.category in (ViolationCategory.CRYPTO_SCAM, ViolationCategory.PHISHING):
            await SanctionsExecutor.ban_user(message.bot, session, chat_id, user_db, reason=verdict.reason)
        elif verdict.suggested_action == SuggestedAction.MUTE_USER:
            await SanctionsExecutor.mute_user(message.bot, session, chat_id, user_db, duration_minutes=60, reason=verdict.reason)
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

        # Record in Audit Logs
        audit_entry = AuditLog(
            chat_id=chat_id,
            user_id=user_db.id,
            action_type=verdict.suggested_action.value,
            category=verdict.category.value,
            reason=verdict.reason,
            confidence=verdict.confidence,
            raw_message_snippet=sanitized.clean_text[:400],
        )
        session.add(audit_entry)
        await session.flush()

        # Send informative moderation card with appeal button to group
        from bot.keyboards.admin_logs import get_group_moderation_keyboard
        user_name = message.from_user.full_name if message.from_user else f"ID {user_id}"
        action_title = "Удаление + Варн"
        if verdict.suggested_action == SuggestedAction.BAN_USER or verdict.category in (ViolationCategory.CRYPTO_SCAM, ViolationCategory.PHISHING):
            action_title = "Удаление + БАН"
        elif verdict.suggested_action == SuggestedAction.MUTE_USER:
            action_title = "Удаление + МУТ"

        notice_text = (
            "<b>TelegramWarden | Модерация</b>\n\n"
            f"• <b>Пользователь:</b> {user_name} (ID: <code>{user_id}</code>)\n"
            f"• <b>Действие:</b> <code>{action_title}</code>\n"
            f"• <b>Причина:</b> {verdict.category.value} ({verdict.confidence}%)\n"
            f"• <b>Пояснение:</b> {verdict.reason}\n\n"
            "<i>Если вы не согласны с решением — нажмите кнопку ниже для подачи апелляции:</i>"
        )
        try:
            await message.bot.send_message(
                chat_id=chat_id,
                text=notice_text,
                reply_markup=get_group_moderation_keyboard(chat_id, user_id, audit_entry.id),
            )
        except Exception as err:
            logger.warning(f"Failed to post group moderation notice: {err}")
