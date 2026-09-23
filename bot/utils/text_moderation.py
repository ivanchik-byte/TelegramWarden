"""Shared text moderation core: sanitize -> risk score -> LLM -> enforce.

Used by the plain-text handler, media captions, document captions and the
edited-message handler so all text payloads follow identical policy.
"""

from datetime import datetime, timezone
from aiogram import Bot
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.notices import send_admin_review_card, send_group_moderation_notice
from bot.utils.sanctions import SanctionsExecutor
from core.logger import logger
from models import AuditLog, Chat, User
from services.ai.client import ai_dispatcher
from services.ai.normalizer import TextSanitizer
from services.ai.risk_scorer import RiskScorer
from services.ai.schema import SuggestedAction, ViolationCategory
from services.moderation.night_mode import is_night_mode_active


# Telegram Bot API entity offsets and lengths are expressed in UTF-16 code units.
# Naive Python string slicing drifts on surrogate pairs (e.g. emojis); encoding
# to UTF-16 LE ensures offsets match Telegram's exact byte positions.
def _slice_utf16(text: str, offset: int, length: int) -> str:
    raw = text.encode("utf-16-le")
    return raw[offset * 2:(offset + length) * 2].decode("utf-16-le", errors="ignore")


def extract_entity_urls(message: Message) -> list[str]:
    """Extract URLs hidden in Telegram formatting entities.

    Spam links routinely hide behind innocent display text via text_link
    entities; the raw message text never contains them.
    """
    urls: list[str] = []
    source_text = message.text or message.caption or ""
    for entity in list(message.entities or []) + list(message.caption_entities or []):
        found: str | None = None
        if entity.type == "url":
            found = _slice_utf16(source_text, entity.offset, entity.length)
        elif entity.type == "text_link" and entity.url:
            found = entity.url
        if found and found not in urls:
            urls.append(found)
    return urls


async def moderate_text_content(
    bot: Bot,
    session: AsyncSession,
    message: Message,
    chat_db: Chat,
    user_db: User,
    raw_text: str,
    source_label: str = "",
) -> bool:
    """Run the full text moderation pipeline over a text payload.

    Returns True when a violation was detected and handled; False when the
    content passed clean. The offending message deletion is included here.
    """
    chat_id = message.chat.id
    user_id = user_db.telegram_id

    sanitized = TextSanitizer.sanitize(raw_text)
    # Hidden-entity links count exactly like visible ones for risk scoring
    hidden_urls = extract_entity_urls(message)
    for url in hidden_urls:
        if url not in sanitized.extracted_urls:
            sanitized.extracted_urls.append(url)

    days_in_chat = (datetime.now(timezone.utc) - user_db.first_seen_at).days
    is_forward = bool(message.forward_origin)

    if not chat_db.full_scan_enabled:
        risk_result = RiskScorer.evaluate(
            sanitized=sanitized,
            user_message_count=user_db.message_count,
            user_days_in_chat=days_in_chat,
            is_forward=is_forward,
            sampling_rate=chat_db.ai_sampling_rate,
            telegram_id=user_id,
        )
        should_call_ai = risk_result.should_call_ai
    else:
        should_call_ai = True

    if not should_call_ai or not chat_db.ai_moderation_enabled:
        return False  # 0 tokens spent, message is clean

    user_context = f"User {user_id}, msgs: {user_db.message_count}, days: {days_in_chat}, warns: {user_db.total_violations_count}"
    verdict = await ai_dispatcher.analyze_message(
        message_text=sanitized.clean_text,
        user_info=user_context,
        cache_chat_id=chat_id,
        cache_user_id=user_id,
        jev_prefilter=getattr(chat_db, "enable_jev_prefilter", True),
        has_hidden_entities=bool(hidden_urls),
    )

    if not verdict.is_violation:
        return False

    if verdict.triaged_by_jev:
        source_label = f"{source_label}[Jev+LLM] "

    cat_key = verdict.category.value
    category_actions = chat_db.category_actions or {}
    custom_action = category_actions.get(cat_key, "ai_default")

    if custom_action == "ignore":
        logger.info(f"Category '{cat_key}' is set to IGNORE in chat {chat_id}. Message passed.")
        return False

    mod_mode = chat_db.moderation_mode or 'ai_judge'
    ban_threshold = chat_db.ai_confidence_threshold if chat_db.ai_confidence_threshold is not None else 85.0
    review_threshold = chat_db.ai_review_threshold if chat_db.ai_review_threshold is not None else 50.0

    if mod_mode == "strict_confidence":
        ban_threshold = max(ban_threshold, 95.0)

    if mod_mode != "ai_judge" and verdict.confidence < review_threshold and custom_action == "ai_default":
        return False  # Under review threshold: clean message, pass

    # Severe contraband escalates only on strong evidence: an LLM hallucination
    # at low confidence must cost a delete+warn, never a permanent ban.
    is_severe_contraband = (
        verdict.category == ViolationCategory.ILLEGAL_CONTRABAND
        and verdict.confidence >= min(ban_threshold, 85.0)
    )
    contraband_suspected = verdict.category == ViolationCategory.ILLEGAL_CONTRABAND

    logger.info(
        f"AI violation flagged in chat {chat_id} by user {user_id}: {cat_key} "
        f"({verdict.confidence}%), mode={mod_mode}, custom_action={custom_action}"
    )

    # Night mode: delete and log for review, defer punitive sanctions
    # (strong contraband evidence stays enforced around the clock)
    if is_night_mode_active(chat_db) and not is_severe_contraband:
        logger.info(f"Night mode active in chat {chat_id}: sanction deferred for user {user_id}")
        await SanctionsExecutor.delete_message(bot, chat_id, message.message_id)
        audit_entry = AuditLog(
            chat_id=chat_id,
            user_id=user_db.id,
            action_type="night_mode_review",
            category=verdict.category.value,
            reason=f"{source_label}[Ночной режим] {verdict.reason}",
            confidence=verdict.confidence,
            raw_message_snippet=sanitized.clean_text[:400],
        )
        session.add(audit_entry)
        await session.flush()
        await send_admin_review_card(
            bot=bot,
            chat_db=chat_db,
            user_name=_display_name(message, user_id),
            user_id=user_id,
            message_preview=sanitized.clean_text,
            category=verdict.category.value,
            confidence=verdict.confidence,
            reason=f"{source_label}{verdict.reason} (ночной режим: санкция отложена)",
            audit_entry_id=audit_entry.id,
        )
        return True

    # Delete message first before applying punitive sanctions
    await SanctionsExecutor.delete_message(bot, chat_id, message.message_id)

    # Custom category actions override default AI Judge behavior
    if custom_action == "delete":
        action_title = "Удаление сообщения"
        action_type = "delete"
    elif custom_action == "warn":
        await SanctionsExecutor.apply_warn(
            bot=bot, session=session, chat_db=chat_db, user_db=user_db,
            reason=f"{source_label}{verdict.reason}", category=cat_key, message_id=message.message_id,
        )
        action_title = "Удаление и варн (по правилу чата)"
        action_type = "warn"
    elif custom_action == "mute":
        await SanctionsExecutor.mute_user(
            bot, session, chat_id, user_db,
            duration_minutes=chat_db.warn_mute_duration_minutes or 1440,
            reason=f"{source_label}{verdict.reason}",
        )
        action_title = "Удаление и мут (по правилу чата)"
        action_type = "mute_user"
    elif custom_action == "ban":
        await SanctionsExecutor.ban_user(bot, session, chat_id, user_db, reason=f"{source_label}{verdict.reason}")
        action_title = "Удаление и бан (по правилу чата)"
        action_type = "ban_user"
    else:
        # Autonomous AI Judge or Strategy Mode
        if mod_mode == "ai_judge":
            # Safety gate: ban_user requires minimal confidence (review_threshold) to prevent low-confidence hallucinated instant bans
            can_ban_in_ai_judge = (
                is_severe_contraband
                or (verdict.suggested_action == SuggestedAction.BAN_USER and verdict.confidence >= review_threshold)
            )
            if can_ban_in_ai_judge:
                await SanctionsExecutor.ban_user(bot, session, chat_id, user_db, reason=f"{source_label}{verdict.reason}")
                action_title = "Удаление и бан (автоматически)"
                action_type = "ban_user"
            elif verdict.suggested_action == SuggestedAction.MUTE_USER:
                await SanctionsExecutor.mute_user(
                    bot, session, chat_id, user_db,
                    duration_minutes=chat_db.warn_mute_duration_minutes or 1440,
                    reason=f"{source_label}{verdict.reason}",
                )
                action_title = "Удаление и мут (автоматически)"
                action_type = "mute_user"
            elif verdict.suggested_action == SuggestedAction.DELETE_MESSAGE:
                action_title = "Удаление сообщения (автоматически)"
                action_type = "delete"
            else:
                await SanctionsExecutor.apply_warn(
                    bot=bot, session=session, chat_db=chat_db, user_db=user_db,
                    reason=f"{source_label}{verdict.reason}", category=cat_key, message_id=message.message_id,
                )
                action_title = f"Удаление и варн ({int(verdict.confidence)}%)"
                action_type = "warn"
        elif mod_mode == "review_only":
            await SanctionsExecutor.apply_warn(
                bot=bot, session=session, chat_db=chat_db, user_db=user_db,
                reason=f"{source_label}{verdict.reason}", category=cat_key, message_id=message.message_id,
            )
            action_title = f"Удаление и рассмотрение ({int(verdict.confidence)}%)"
            action_type = "warn"
        elif is_severe_contraband or (
            not contraband_suspected and verdict.confidence >= ban_threshold
        ):
            # High Confidence Tier -> Ban (low-confidence contraband stays a warn)
            await SanctionsExecutor.ban_user(bot, session, chat_id, user_db, reason=f"{source_label}{verdict.reason}")
            action_title = f"Удаление и бан ({int(verdict.confidence)}%)"
            action_type = "ban_user"
        else:
            # Review Tier -> Warn
            await SanctionsExecutor.apply_warn(
                bot=bot, session=session, chat_db=chat_db, user_db=user_db,
                reason=f"{source_label}{verdict.reason}", category=cat_key, message_id=message.message_id,
            )
            action_title = f"Удаление и варн ({int(verdict.confidence)}%)"
            action_type = "warn"

    audit_entry = AuditLog(
        chat_id=chat_id,
        user_id=user_db.id,
        action_type=action_type,
        category=verdict.category.value,
        reason=f"{source_label}{verdict.reason}",
        confidence=verdict.confidence,
        raw_message_snippet=sanitized.clean_text[:400],
    )
    session.add(audit_entry)
    await session.flush()

    await send_group_moderation_notice(
        bot=bot,
        chat_id=chat_id,
        user_name=_display_name(message, user_id),
        user_id=user_id,
        action_title=action_title,
        category=verdict.category.value,
        confidence=verdict.confidence,
        reason=f"{source_label}{verdict.reason}",
        audit_entry_id=audit_entry.id,
    )

    if chat_db.send_suspicious_to_admin:
        await send_admin_review_card(
            bot=bot,
            chat_db=chat_db,
            user_name=_display_name(message, user_id),
            user_id=user_id,
            message_preview=sanitized.clean_text,
            category=verdict.category.value,
            confidence=verdict.confidence,
            reason=f"{source_label}{verdict.reason}",
            audit_entry_id=audit_entry.id,
            is_ban_action=(action_type == "ban_user"),
        )

    return True


def _display_name(message: Message, user_id: int) -> str:
    return message.from_user.full_name if message.from_user else f"ID {user_id}"
