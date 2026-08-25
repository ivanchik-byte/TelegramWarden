"""Message moderation handler for text, forwards, channels, and inline bots."""

from datetime import datetime, timezone
from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.guards import enforce_source_guards
from bot.utils.notices import send_admin_review_card, send_group_moderation_notice
from bot.utils.sanctions import SanctionsExecutor
from core.logger import logger
from models import Chat, AuditLog
from services.ai.client import ai_dispatcher
from services.ai.normalizer import TextSanitizer
from services.ai.risk_scorer import RiskScorer
from services.ai.schema import SuggestedAction, ViolationCategory
from services.moderation.night_mode import is_night_mode_active

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

    # 2. Anti-Channel / Anti-Inline bot source protection (shared guard)
    if not await enforce_source_guards(message, chat_db):
        return

    if not message.from_user:
        return

    user_id = message.from_user.id
    if user_id in (chat_db.whitelisted_users or []):
        return  # Whitelisted user bypass

    # 3. Get or create permanent user profile
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

    # 8. Tiered AI Action Enforcement with Category Overrides & AI Judge Mode
    category_actions = chat_db.category_actions or {}
    cat_key = verdict.category.value if hasattr(verdict.category, 'value') else str(verdict.category)
    custom_action = category_actions.get(cat_key, "ai_default")

    # Custom override: Ignore category completely (e.g. "не удалять оскорбления")
    if custom_action == "ignore":
        logger.info(f"Category '{cat_key}' is set to IGNORE in chat {chat_id}. Message passed.")
        return

    mod_mode = getattr(chat_db, 'moderation_mode', 'ai_judge') or 'ai_judge'
    ban_threshold = chat_db.ai_confidence_threshold or 85.0
    review_threshold = getattr(chat_db, 'ai_review_threshold', 50.0) or 50.0

    if mod_mode == "strict_confidence":
        ban_threshold = max(ban_threshold, 95.0)

    # Check if confidence meets minimum review threshold (unless AI Judge decided action)
    if mod_mode != "ai_judge" and verdict.confidence < review_threshold and custom_action == "ai_default":
        return  # Under review threshold: Clean message, pass

    # Always instant ban severe contraband regardless of lower threshold
    is_severe_contraband = (verdict.category == ViolationCategory.ILLEGAL_CONTRABAND)

    logger.info(f"AI violation flagged in chat {chat_id} by user {user_id}: {cat_key} ({verdict.confidence}%), mode={mod_mode}, custom_action={custom_action}")

    # Night mode: delete and log for review, defer punitive sanctions
    if is_night_mode_active(chat_db) and not is_severe_contraband:
        logger.info(f"Night mode active in chat {chat_id}: sanction deferred for user {user_id}")
        await SanctionsExecutor.delete_message(message.bot, chat_id, message.message_id)

        audit_entry = AuditLog(
            chat_id=chat_id,
            user_id=user_db.id,
            action_type="night_mode_review",
            category=verdict.category.value,
            reason=f"[Ночной режим] {verdict.reason}",
            confidence=verdict.confidence,
            raw_message_snippet=sanitized.clean_text[:400],
        )
        session.add(audit_entry)
        await session.flush()

        await send_admin_review_card(
            bot=message.bot,
            chat_db=chat_db,
            user_name=message.from_user.full_name if message.from_user else f"ID {user_id}",
            user_id=user_id,
            message_preview=sanitized.clean_text,
            category=verdict.category.value,
            confidence=verdict.confidence,
            reason=f"{verdict.reason} (ночной режим — санкция отложена)",
            audit_entry_id=audit_entry.id,
        )
        return

    # Delete offending message
    await SanctionsExecutor.delete_message(message.bot, chat_id, message.message_id)

    # If custom action is explicitly set by admin, enforce it directly
    if custom_action == "delete":
        action_title = "Удаление сообщения"
        action_type = "delete"
    elif custom_action == "warn":
        await SanctionsExecutor.apply_warn(
            bot=message.bot,
            session=session,
            chat_db=chat_db,
            user_db=user_db,
            reason=verdict.reason,
            category=cat_key,
            message_id=message.message_id,
        )
        action_title = "Удаление + Варн (По правилу чата)"
        action_type = "warn"
    elif custom_action == "mute":
        await SanctionsExecutor.mute_user(message.bot, session, chat_id, user_db, duration_minutes=chat_db.warn_mute_duration_minutes or 1440, reason=verdict.reason)
        action_title = f"Удаление + МУТ (По правилу чата)"
        action_type = "mute_user"
    elif custom_action == "ban":
        await SanctionsExecutor.ban_user(message.bot, session, chat_id, user_db, reason=verdict.reason)
        action_title = "Удаление + БАН (По правилу чата)"
        action_type = "ban_user"
    else:
        # Autonomous AI Judge or Strategy Mode
        if mod_mode == "ai_judge":
            # AI Judge decides autonomously
            if is_severe_contraband or verdict.suggested_action == SuggestedAction.BAN_USER:
                await SanctionsExecutor.ban_user(message.bot, session, chat_id, user_db, reason=verdict.reason)
                action_title = f"Удаление + БАН (Вердикт ИИ-Судьи)"
                action_type = "ban_user"
            elif verdict.suggested_action == SuggestedAction.MUTE_USER:
                await SanctionsExecutor.mute_user(message.bot, session, chat_id, user_db, duration_minutes=chat_db.warn_mute_duration_minutes or 1440, reason=verdict.reason)
                action_title = f"Удаление + МУТ (Вердикт ИИ-Судьи)"
                action_type = "mute_user"
            elif verdict.suggested_action == SuggestedAction.DELETE_MESSAGE:
                action_title = "Удаление (Вердикт ИИ-Судьи)"
                action_type = "delete"
            else:
                await SanctionsExecutor.apply_warn(
                    bot=message.bot,
                    session=session,
                    chat_db=chat_db,
                    user_db=user_db,
                    reason=verdict.reason,
                    category=cat_key,
                    message_id=message.message_id,
                )
                action_title = f"Удаление + Варн (Вердикт ИИ-Судьи, {int(verdict.confidence)}%)"
                action_type = "warn"
        elif mod_mode == "review_only":
            await SanctionsExecutor.apply_warn(
                bot=message.bot,
                session=session,
                chat_db=chat_db,
                user_db=user_db,
                reason=verdict.reason,
                category=cat_key,
                message_id=message.message_id,
            )
            action_title = f"Удаление + На рассмотрение (Мягкий режим, {int(verdict.confidence)}%)"
            action_type = "warn"
        elif is_severe_contraband or verdict.confidence >= ban_threshold:
            # High Confidence Tier -> Ban
            await SanctionsExecutor.ban_user(message.bot, session, chat_id, user_db, reason=verdict.reason)
            action_title = f"Удаление + БАН ({int(verdict.confidence)}% Уверенность)"
            action_type = "ban_user"
        else:
            # Review Tier -> Warn
            await SanctionsExecutor.apply_warn(
                bot=message.bot,
                session=session,
                chat_db=chat_db,
                user_db=user_db,
                reason=verdict.reason,
                category=cat_key,
                message_id=message.message_id,
            )
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
    user_name = message.from_user.full_name if message.from_user else f"ID {user_id}"
    await send_group_moderation_notice(
        bot=message.bot,
        chat_id=chat_id,
        user_name=user_name,
        user_id=user_id,
        action_title=action_title,
        category=verdict.category.value,
        confidence=verdict.confidence,
        reason=verdict.reason,
        audit_entry_id=audit_entry.id,
    )

    # Send admin review card (log channel, falling back to the group chat)
    if chat_db.send_suspicious_to_admin:
        await send_admin_review_card(
            bot=message.bot,
            chat_db=chat_db,
            user_name=user_name,
            user_id=user_id,
            message_preview=sanitized.clean_text,
            category=verdict.category.value,
            confidence=verdict.confidence,
            reason=verdict.reason,
            audit_entry_id=audit_entry.id,
            is_ban_action=(action_type == "ban_user"),
        )


