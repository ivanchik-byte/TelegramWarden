"""Handlers for admin actions on audit log cards (unban, unwarn, false positive feedback)."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, ChatPermissions
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.logger import logger
from models import AuditLog, User, Warn

router = Router(name="admin_actions")

UNRESTRICTED_PERMISSIONS = ChatPermissions(
    can_send_messages=True,
    can_send_media_messages=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
)


@router.callback_query(F.data.startswith("log:unban:"))
async def handle_admin_unban(callback: CallbackQuery, session: AsyncSession) -> None:
    """Unban user from Telegram chat and update database status."""
    if not callback.message or not callback.data:
        return

    parts = callback.data.split(":")
    if len(parts) != 5:
        return

    chat_id = int(parts[2])
    telegram_id = int(parts[3])
    log_id = int(parts[4])
    admin_id = callback.from_user.id

    try:
        # Unban in Telegram
        await callback.bot.unban_chat_member(chat_id=chat_id, user_id=telegram_id, only_if_banned=True)

        # Update User in DB
        res_u = await session.execute(
            select(User).where(User.chat_id == chat_id, User.telegram_id == telegram_id)
        )
        user_db = res_u.scalar_one_or_none()
        if user_db:
            user_db.is_banned = False
            user_db.ban_reason = None
            user_db.banned_at = None

        # Update AuditLog
        audit_entry = await session.get(AuditLog, log_id)
        if audit_entry:
            audit_entry.reviewed_by_admin_id = admin_id
            audit_entry.admin_action_taken = "unbanned"

        admin_name = callback.from_user.first_name or f"Admin {admin_id}"
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply(text=f"Пользователь разблокирован администратором {admin_name}.")
        await callback.answer(text="Пользователь успешно разбанен!")
        logger.info(f"Admin {admin_id} unbanned user {telegram_id} in {chat_id}")

    except Exception as err:
        logger.error(f"Failed to execute admin unban: {err}")
        await callback.answer(text="Ошибка при разбане пользователя.", show_alert=True)


@router.callback_query(F.data.startswith("log:unwarn:"))
async def handle_admin_unwarn(callback: CallbackQuery, session: AsyncSession) -> None:
    """Remove active warning for user and restore permissions."""
    if not callback.message or not callback.data:
        return

    parts = callback.data.split(":")
    if len(parts) != 5:
        return

    chat_id = int(parts[2])
    telegram_id = int(parts[3])
    log_id = int(parts[4])
    admin_id = callback.from_user.id

    try:
        # Deactivate latest active warn
        res_u = await session.execute(
            select(User).where(User.chat_id == chat_id, User.telegram_id == telegram_id)
        )
        user_db = res_u.scalar_one_or_none()
        if user_db:
            res_w = await session.execute(
                select(Warn)
                .where(Warn.user_id == user_db.id, Warn.chat_id == chat_id, Warn.is_active == True)  # noqa: E712
                .order_by(Warn.id.desc())
            )
            warn_db = res_w.scalars().first()
            if warn_db:
                warn_db.is_active = False

        # Update AuditLog
        audit_entry = await session.get(AuditLog, log_id)
        if audit_entry:
            audit_entry.reviewed_by_admin_id = admin_id
            audit_entry.admin_action_taken = "warn_removed"

        admin_name = callback.from_user.first_name or f"Admin {admin_id}"
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply(text=f"Предупреждение снято администратором {admin_name}.")
        await callback.answer(text="Предупреждение успешно снято!")
        logger.info(f"Admin {admin_id} removed warn for user {telegram_id} in {chat_id}")

    except Exception as err:
        logger.error(f"Failed to unwarn user: {err}")
        await callback.answer(text="Ошибка при снятии варна.", show_alert=True)


@router.callback_query(F.data.startswith("log:ban:"))
async def handle_admin_ban_action(callback: CallbackQuery, session: AsyncSession) -> None:
    """Ban user directly from admin verification card."""
    if not callback.message or not callback.data:
        return

    parts = callback.data.split(":")
    if len(parts) != 5:
        return

    chat_id = int(parts[2])
    telegram_id = int(parts[3])
    log_id = int(parts[4])
    admin_id = callback.from_user.id

    try:
        from bot.utils.sanctions import SanctionsExecutor
        res_u = await session.execute(
            select(User).where(User.chat_id == chat_id, User.telegram_id == telegram_id)
        )
        user_db = res_u.scalar_one_or_none()
        if user_db:
            await SanctionsExecutor.ban_user(callback.bot, session, chat_id, user_db, reason="Бан по решению администратора")

        audit_entry = await session.get(AuditLog, log_id)
        if audit_entry:
            audit_entry.reviewed_by_admin_id = admin_id
            audit_entry.admin_action_taken = "banned_by_admin"

        admin_name = callback.from_user.first_name or f"Admin {admin_id}"
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply(text=f"⛔ Пользователь заблокирован администратором {admin_name}.")
        await callback.answer(text="Пользователь забанен!")
        logger.info(f"Admin {admin_id} banned user {telegram_id} in {chat_id}")
    except Exception as err:
        logger.error(f"Failed to ban user from admin card: {err}")
        await callback.answer(text="Ошибка при бане пользователя.", show_alert=True)


@router.callback_query(F.data.startswith("log:mute:"))
async def handle_admin_mute_action(callback: CallbackQuery, session: AsyncSession) -> None:
    """Mute user directly from admin verification card."""
    if not callback.message or not callback.data:
        return

    parts = callback.data.split(":")
    if len(parts) != 5:
        return

    chat_id = int(parts[2])
    telegram_id = int(parts[3])
    log_id = int(parts[4])
    admin_id = callback.from_user.id

    try:
        from bot.utils.sanctions import SanctionsExecutor
        res_u = await session.execute(
            select(User).where(User.chat_id == chat_id, User.telegram_id == telegram_id)
        )
        user_db = res_u.scalar_one_or_none()
        if user_db:
            await SanctionsExecutor.mute_user(callback.bot, session, chat_id, user_db, duration_minutes=1440, reason="Мут по решению администратора")

        audit_entry = await session.get(AuditLog, log_id)
        if audit_entry:
            audit_entry.reviewed_by_admin_id = admin_id
            audit_entry.admin_action_taken = "muted_by_admin"

        admin_name = callback.from_user.first_name or f"Admin {admin_id}"
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply(text=f"🔇 Пользователь отправлен в мут администратором {admin_name}.")
        await callback.answer(text="Пользователь замучен на 24 часа!")
        logger.info(f"Admin {admin_id} muted user {telegram_id} in {chat_id}")
    except Exception as err:
        logger.error(f"Failed to mute user from admin card: {err}")
        await callback.answer(text="Ошибка при муте пользователя.", show_alert=True)


@router.callback_query(F.data.startswith("log:false_pos:"))
async def handle_admin_false_positive(callback: CallbackQuery, session: AsyncSession) -> None:
    """Mark moderation action as false positive for prompt optimization feedback loop."""
    if not callback.message or not callback.data:
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        return

    log_id = int(parts[2])
    admin_id = callback.from_user.id

    try:
        audit_entry = await session.get(AuditLog, log_id)
        if audit_entry:
            audit_entry.is_false_positive = True
            audit_entry.reviewed_by_admin_id = admin_id
            audit_entry.admin_action_taken = "marked_false_positive"

        admin_name = callback.from_user.first_name or f"Admin {admin_id}"
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply(text=f"✅ Действие помечено как ложное срабатывание администратором {admin_name}.")
        await callback.answer(text="Отметка о ложном срабатывании сохранена для улучшения ИИ!")
        logger.info(f"Admin {admin_id} marked log {log_id} as false positive")

    except Exception as err:
        logger.error(f"Failed to mark false positive: {err}")
        await callback.answer(text="Ошибка при сохранении обратной связи.", show_alert=True)

