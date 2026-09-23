"""Interactive appeal and /report handling router."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.admin_logs import get_admin_appeal_review_keyboard
from html import escape as quote
from bot.utils.admin_checker import is_chat_admin
from core.config import settings
from core.logger import logger
from core.redis_client import redis_manager
from models import AuditLog, Chat, User, Warn
from services.ai.client import ai_dispatcher
from services.ai.normalizer import TextSanitizer
from bot.utils.sanctions import SanctionsExecutor

router = Router(name="appeals")


@router.callback_query(F.data.startswith("appeal:open:"))
async def handle_open_appeal_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    """Submit moderation appeal from group notice card."""
    parts = callback.data.split(":")
    if len(parts) != 5:
        return

    try:
        chat_id = int(parts[2])
        target_user_id = int(parts[3])
        log_id = int(parts[4])
    except ValueError:
        return
    caller_id = callback.from_user.id

    result = await session.execute(select(AuditLog).where(AuditLog.id == log_id))
    log_entry = result.scalar_one_or_none()

    if not log_entry:
        await callback.answer("Запись инцидента не найдена.", show_alert=True)
        return

    if log_entry.chat_id != chat_id:
        await callback.answer("Запись не относится к этому чату.", show_alert=True)
        return

    try:
        redis = await redis_manager.get_client()
        throttle_key = f"warden:appeal:{caller_id}:{log_id}"
        if await redis.get(throttle_key):
            await callback.answer("Апелляция уже отправлена. Повторите через час.", show_alert=True)
            return
        await redis.set(throttle_key, "1", ex=3600)
    except Exception:
        pass

    caller_name = callback.from_user.full_name or callback.from_user.username or str(caller_id)
    appeal_text = (
        "<b>Новая апелляция на модерацию!</b>\n\n"
        f"• <b>Чат:</b> <code>{chat_id}</code>\n"
        f"• <b>Пользователь:</b> (ID: <code>{target_user_id}</code>)\n"
        f"• <b>Податель апелляции:</b> {quote(caller_name)} (ID: <code>{caller_id}</code>)\n"
        f"• <b>Причина санкции:</b> {quote(log_entry.category or '')} ({log_entry.confidence or 0}%)\n"
        f"• <b>Текст сообщения:</b>\n<i>{quote(log_entry.raw_message_snippet or 'Медиа/текст')}</i>\n\n"
        "Выберите действие:"
    )
    review_kb = get_admin_appeal_review_keyboard(chat_id, target_user_id, log_id)

    # Send notification to superadmins
    for superadmin_id in settings.superadmin_id_list:
        try:
            await callback.bot.send_message(
                chat_id=superadmin_id,
                text=appeal_text,
                reply_markup=review_kb,
            )
        except Exception as err:
            logger.debug(f"Failed to send appeal alert to superadmin {superadmin_id}: {err}")

    if callback.message:
        try:
            await callback.message.edit_text(
                text=f"{callback.message.text}\n\n<b>Статус: Апелляция отправлена администрации на перепроверку.</b>"
            )
        except Exception:
            pass

    await callback.answer("Ваша апелляция успешно отправлена администрации чата!", show_alert=True)
    logger.info(f"User {caller_id} appealed moderation log #{log_id} in chat {chat_id}")


@router.callback_query(F.data.startswith("appeal:accept:"))
async def handle_appeal_accept(callback: CallbackQuery, session: AsyncSession) -> None:
    """Admin approves appeal: unban/unwarn user and restore reputation."""
    parts = callback.data.split(":")
    try:
        chat_id = int(parts[2])
        target_user_id = int(parts[3])
        log_id = int(parts[4])
    except ValueError:
        return
    admin_id = callback.from_user.id

    has_rights = await is_chat_admin(callback.bot, chat_id, admin_id)
    if not has_rights:
        await callback.answer("У вас нет прав для одобрения апелляций.", show_alert=True)
        return

    try:
        await callback.bot.unban_chat_member(chat_id=chat_id, user_id=target_user_id, only_if_banned=True)
    except Exception as err:
        logger.warning(f"Failed to unban user {target_user_id} in {chat_id}: {err}")

    u_res = await session.execute(select(User).where(User.telegram_id == target_user_id, User.chat_id == chat_id))
    user_db = u_res.scalar_one_or_none()
    if user_db:
        warns = (
            await session.execute(
                select(Warn).where(
                    Warn.user_id == user_db.id,
                    Warn.chat_id == chat_id,
                    Warn.is_active == True,  # noqa: E712
                )
            )
        ).scalars().all()
        for w in warns:
            await session.delete(w)
        user_db.is_banned = False
        user_db.is_muted = False
        user_db.muted_until = None
        await session.commit()

    admin_name = callback.from_user.full_name or callback.from_user.username or str(admin_id)
    await callback.message.edit_text(
        f"<b>Апелляция ОДОБРЕНА администратором {admin_name}!</b>\n\nПользователь <code>{target_user_id}</code> разбанен, все предупреждения сняты."
    )
    await callback.answer("Апелляция одобрена, пользователь разблокирован!", show_alert=True)
    logger.info(f"Admin {admin_id} accepted appeal for user {target_user_id} in chat {chat_id}")


@router.callback_query(F.data.startswith("appeal:reject:"))
async def handle_appeal_reject(callback: CallbackQuery) -> None:
    """Admin rejects appeal: keep sanctions."""
    parts = (callback.data or "").split(":")
    if len(parts) != 5:
        return
    try:
        chat_id = int(parts[2])
    except ValueError:
        return
    admin_id = callback.from_user.id
    if not await is_chat_admin(callback.bot, chat_id, admin_id):
        await callback.answer("У вас нет прав для отклонения апелляций.", show_alert=True)
        return
    admin_name = callback.from_user.full_name or callback.from_user.username or str(admin_id)

    await callback.message.edit_text(
        f"<b>Апелляция ОТКЛОНЕНА администратором {quote(admin_name)}.</b>\n\nСанкции остаются в силе."
    )
    await callback.answer("Апелляция отклонена.")

