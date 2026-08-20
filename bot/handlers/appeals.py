"""Interactive appeal and /report handling router."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.admin_logs import get_admin_appeal_review_keyboard
from bot.utils.admin_checker import is_chat_admin
from core.config import settings
from core.logger import logger
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

    chat_id = int(parts[2])
    target_user_id = int(parts[3])
    log_id = int(parts[4])
    caller_id = callback.from_user.id

    # Fetch audit log entry
    result = await session.execute(select(AuditLog).where(AuditLog.id == log_id))
    log_entry = result.scalar_one_or_none()

    if not log_entry:
        await callback.answer("Запись инцидента не найдена.", show_alert=True)
        return

    # Notify all superadmins in DM about the appeal
    caller_name = callback.from_user.full_name or callback.from_user.username or str(caller_id)
    appeal_text = (
        "<b>Новая апелляция на модерацию!</b>\n\n"
        f"• <b>Чат:</b> <code>{chat_id}</code>\n"
        f"• <b>Пользователь:</b> (ID: <code>{target_user_id}</code>)\n"
        f"• <b>Податель апелляции:</b> {caller_name} (ID: <code>{caller_id}</code>)\n"
        f"• <b>Причина санкции:</b> {log_entry.category} ({log_entry.confidence}%)\n"
        f"• <b>Текст сообщения:</b>\n<i>{log_entry.raw_message_snippet or 'Медиа/текст'}</i>\n\n"
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

    # Update group card status
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
    chat_id = int(parts[2])
    target_user_id = int(parts[3])
    log_id = int(parts[4])
    admin_id = callback.from_user.id

    has_rights = await is_chat_admin(callback.bot, chat_id, admin_id)
    if not has_rights:
        await callback.answer("У вас нет прав для одобрения апелляций.", show_alert=True)
        return

    # Unban in Telegram
    try:
        await callback.bot.unban_chat_member(chat_id=chat_id, user_id=target_user_id, only_if_banned=True)
    except Exception as err:
        logger.warning(f"Failed to unban user {target_user_id} in {chat_id}: {err}")

    # Remove warns from database
    u_res = await session.execute(select(User).where(User.telegram_id == target_user_id, User.chat_id == chat_id))
    user_db = u_res.scalar_one_or_none()
    if user_db:
        warns = (await session.execute(select(Warn).where(Warn.user_id == user_db.id, Warn.chat_id == chat_id))).scalars().all()
        for w in warns:
            await session.delete(w)
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
    admin_id = callback.from_user.id
    admin_name = callback.from_user.full_name or callback.from_user.username or str(admin_id)

    await callback.message.edit_text(
        f"<b>Апелляция ОТКЛОНЕНА администратором {admin_name}.</b>\n\nСанкции остаются в силе."
    )
    await callback.answer("Апелляция отклонена.")


# =========================================================================
# /report command in group chats
# =========================================================================

@router.message(Command("report"))
async def handle_report_command(message: Message, session: AsyncSession) -> None:
    """Report a message to group administrators and run instant AI moderation."""
    if message.chat.id > 0:
        await message.reply("Команда /report используется в группах ответом на подозрительное сообщение.")
        return

    # User must reply to a message
    if not message.reply_to_message:
        await message.reply("Ответьте командой <code>/report</code> на сообщение, которое хотите отправить на проверку.")
        return

    target_msg = message.reply_to_message
    target_user = target_msg.from_user
    if not target_user:
        return

    reporter = message.from_user
    reporter_name = reporter.full_name if reporter else "Участник"

    # Analyze target message with AI
    raw_text = target_msg.text or target_msg.caption or ""
    sanitized = TextSanitizer.sanitize(raw_text)

    status_msg = await message.reply("Жалоба принята. Проверяю сообщение через нейросеть...")

    verdict = await ai_dispatcher.analyze_message(
        message_text=sanitized.clean_text,
        user_info=f"Reported message from {target_user.id}",
    )

    if verdict.is_violation:
        # Delete reported message
        try:
            await target_msg.delete()
        except Exception:
            pass

        # Apply warn/ban
        u_res = await session.execute(select(User).where(User.telegram_id == target_user.id, User.chat_id == message.chat.id))
        user_db = u_res.scalar_one_or_none()
        if not user_db:
            user_db = User(telegram_id=target_user.id, chat_id=message.chat.id, username=target_user.username)
            session.add(user_db)
            await session.flush()

        await SanctionsExecutor.ban_user(message.bot, session, message.chat.id, user_db, reason=verdict.reason)

        await status_msg.edit_text(
            f"<b>Спасибо за жалобу, {reporter_name}!</b>\n\n"
            f"ИИ подтвердил нарушение (<code>{verdict.category.value}</code>, {verdict.confidence}%).\n"
            f"Сообщение удалено, нарушитель <b>{target_user.full_name}</b> заблокирован."
        )
    else:
        await status_msg.edit_text(
            f"<b>Жалоба от {reporter_name} проверена.</b>\n\n"
            "Признаков явного спама или вредоносных ссылок нейросетью не обнаружено. Информация передана администраторам."
        )
