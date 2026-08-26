"""Periodic digest of night-mode deferred sanctions.

Deferred sanctions are only useful if admins actually see them: this loop
watches every active chat and, once its night window has ended and unreviewed
night_mode_review entries exist, posts a consolidated morning digest to the
log channel (or the chat itself) with per-user counts.
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import func, select

from core.database import async_session_factory
from core.logger import logger
from core.redis_client import redis_manager
from models import AuditLog, Chat, User
from services.moderation.night_mode import get_night_mode_status

DIGEST_CHECK_INTERVAL_SECONDS = 15 * 60
REDIS_DIGEST_MARKER_PREFIX = "warden:nightdigest:"


async def _collect_pending_digest(session, chat_db: Chat):
    """Return per-user deferred-violation stats since the last digest."""
    redis = await redis_manager.get_client()
    marker_key = f"{REDIS_DIGEST_MARKER_PREFIX}{chat_db.chat_id}"
    marker = await redis.get(marker_key)
    since = datetime.fromtimestamp(float(marker), tz=timezone.utc) if marker else None

    query = (
        select(
            User.telegram_id,
            func.coalesce(User.username, User.first_name, User.telegram_id),
            func.count(AuditLog.id),
        )
        .join(User, AuditLog.user_id == User.id)
        .where(
            AuditLog.chat_id == chat_db.chat_id,
            AuditLog.action_type == "night_mode_review",
        )
        .group_by(User.telegram_id, User.username, User.first_name)
    )
    if since:
        query = query.where(AuditLog.created_at > since)

    rows = (await session.execute(query)).all()
    return rows, marker_key


async def process_chat_digest(bot, session, chat_db: Chat) -> None:
    """Send the morning digest for one chat when it is due."""
    if get_night_mode_status(chat_db).is_active:
        return  # still night: sanctions are being deferred, nothing to report yet

    rows, marker_key = await _collect_pending_digest(session, chat_db)
    if not rows:
        return

    total = sum(count for _, _, count in rows)
    lines = "\n".join(
        f"• {name} (<code>{telegram_id}</code>) — {count} наруш." for telegram_id, name, count in rows
    )
    text = (
        " <b>TelegramWarden | Итоги ночного режима</b>\n\n"
        f"За ночь отложено санкций: <b>{total}</b>\n{lines}\n\n"
        "<i>Карточки с кнопками разбана/бана отправлялись в чат по ходу нарушений. "
        "Проверьте их и примените санкции вручную.</i>"
    )

    target = chat_db.log_channel_id or chat_db.chat_id
    try:
        await bot.send_message(chat_id=target, text=text)
    except Exception as send_err:
        logger.warning(f"Failed to deliver night digest to {target}: {send_err}")
        return

    redis = await redis_manager.get_client()
    await redis.set(marker_key, datetime.now(timezone.utc).timestamp())


async def run_night_digest_loop(bot) -> None:
    """Background loop: check every active chat for a due night digest."""
    logger.info("Night digest scheduler started.")
    while True:
        await asyncio.sleep(DIGEST_CHECK_INTERVAL_SECONDS)
        try:
            async with async_session_factory() as session:
                result = await session.execute(select(Chat).where(Chat.is_active == True))  # noqa: E712
                for chat_db in result.scalars():
                    try:
                        await process_chat_digest(bot, session, chat_db)
                    except Exception as chat_err:
                        logger.warning(f"Night digest failed for chat {chat_db.chat_id}: {chat_err}")
                await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception as loop_err:
            logger.error(f"Night digest loop error: {loop_err}")
