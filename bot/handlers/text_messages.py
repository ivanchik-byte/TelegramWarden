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

    full_scan = getattr(chat_db, 'full_scan_enabled', False)
    if full_scan:
        should_call_ai = True
    else:
        risk_result = RiskScorer.evaluate(
            sanitized=sanitized,
            user_message_count=user_db.message_count,
            user_days_in_chat=days_in_chat,
            is_forward=is_forward,
            sampling_rate=chat_db.ai_sampling_rate,
        )
        should_call_ai = risk_result.should_call_ai

    if not should_call_ai or not chat_db.ai_moderation_enabled:
        return  # 0 tokens spent, message is clean

    # 7. Query AI Intent Engine
    user_context = f"User {user_id}, msgs: {user_db.message_count}, days: {days_in_chat}, warns: {user_db.total_violations_count}"
    verdict = await ai_dispatcher.analyze_message(
        message_text=sanitized.clean_text,
        user_info=user_context,
    )

    if not verdict.is_violation:
        return

    # 8. Tiered AI Action Enforcement with Moderation Mode Strategy
    mod_mode = getattr(chat_db, 'moderation_mode', 'standard') or 'standard'
    ban_threshold = chat_db.ai_confidence_threshold or 85.0
    review_threshold = getattr(chat_db, 'ai_review_threshold', 50.0) or 50.0

    if mod_mode == "strict_confidence":
        ban_threshold = max(ban_threshold, 95.0)

    if verdict.confidence < review_threshold:
        return  # Under review threshold: Clean message, pass

    # Always instant ban severe contraband regardless of lower threshold
    is_severe_contraband = (verdict.category == ViolationCategory.ILLEGAL_CONTRABAND)

    logger.info(f"AI violation flagged in chat {chat_id} by user {user_id}: {verdict.category} ({verdict.confidence}%), mode={mod_mode}")

    # Delete offending message
    await SanctionsExecutor.delete_message(message.bot, chat_id, message.message_id)

    # Determine if ban/mute should be applied or purely soft review
    should_hard_punish = False
    if mod_mode == "review_only":
        should_hard_punish = False  # Never auto-ban in Review-Only mode
    elif is_severe_contraband or verdict.confidence >= ban_threshold:
        should_hard_punish = True

    # Enforce action based on strategy
    if should_hard_punish:
        # Hard Sanction (Ban / Mute)
        if verdict.suggested_action == SuggestedAction.BAN_USER or verdict.category in (
            ViolationCategory.CRYPTO_SCAM,
            ViolationCategory.PHISHING,
            ViolationCategory.ILLEGAL_CONTRABAND,
        ):
            await SanctionsExecutor.ban_user(message.bot, session, chat_id, user_db, reason=verdict.reason)
            action_title = f"Удаление + БАН ({int(verdict.confidence)}% Уверенность)"
            action_type = "ban_user"
        elif verdict.suggested_action == SuggestedAction.MUTE_USER:
            await SanctionsExecutor.mute_user(message.bot, session, chat_id, user_db, duration_minutes=chat_db.warn_mute_duration_minutes or 1440, reason=verdict.reason)
            action_title = f"Удаление + МУТ ({int(verdict.confidence)}% Уверенность)"
            action_type = "mute_user"
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
            action_title = "Удаление + Варн"
            action_type = "warn"
    else:
        # Soft Sanction (Warning / On Review)
        await SanctionsExecutor.apply_warn(
            bot=message.bot,
            session=session,
            chat_db=chat_db,
            user_db=user_db,
            reason=verdict.reason,
            category=verdict.category.value,
            message_id=message.message_id,
        )
        if mod_mode == "review_only":
            action_title = f"Удаление + На рассмотрение (Мягкий режим, {int(verdict.confidence)}%)"
        else:
            action_title = f"Удаление + Предупреждение ({int(verdict.confidence)}% На проверке)"
        action_type = "warn"

    # Record in Audit Logs
    audit_entry = AuditLog(
        chat_id=chat_id,
        user_id=user_db.id,
        action_type=action_type,
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

