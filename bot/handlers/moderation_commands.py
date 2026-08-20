"""Manual moderation commands router for chat administrators (/warn, /unwarn, /mute, /ban)."""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.admin_logs import get_group_moderation_keyboard
from bot.utils.admin_checker import is_chat_admin, is_superadmin
from bot.utils.sanctions import SanctionsExecutor, MUTE_PERMISSIONS
from core.config import settings
from core.logger import logger
from models import AuditLog, Chat, User, Warn

router = Router(name="moderation_commands")


def parse_duration_string(duration_str: str) -> Optional[int]:
    """Parse time string like '30m', '2h', '1d', '7d' into minutes."""
    match = re.match(r"^(\d+)([mhd])$", duration_str.lower().strip())
    if not match:
        return None
    val, unit = int(match.group(1)), match.group(2)
    if unit == "m":
        return val
    elif unit == "h":
        return val * 60
    elif unit == "d":
        return val * 1440
    return None


@router.message(Command("warn"))
async def handle_manual_warn_command(message: Message, session: AsyncSession) -> None:
    """Issue manual warning to a user in reply."""
    if message.chat.id > 0:
        return

    chat_id = message.chat.id
    admin_user = message.from_user
    admin_id = admin_user.id if admin_user else 0

    # Fetch Chat DB
    res_c = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = res_c.scalar_one_or_none()
    if not chat_db:
        chat_db = Chat(chat_id=chat_id, title=message.chat.title or "Chat")
        session.add(chat_db)
        await session.flush()

    if not await is_chat_admin(message.bot, chat_id, admin_id, chat_db):
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply("Ответьте командой <code>/warn [причина]</code> на сообщение нарушителя.")
        return

    target_user = message.reply_to_message.from_user
    if target_user.is_bot:
        await message.reply("Ботам нельзя выдавать предупреждения.")
        return

    # Check if target is admin
    if await is_chat_admin(message.bot, chat_id, target_user.id, chat_db):
        await message.reply("Нельзя выдать предупреждение администратору чата.")
        return

    # Parse reason
    parts = (message.text or "").split(maxsplit=1)
    reason = parts[1] if len(parts) > 1 else "Нарушение правил чата"

    # Get target user record in DB
    user_db = await SanctionsExecutor.get_or_create_user(
        session=session,
        chat_id=chat_id,
        telegram_id=target_user.id,
        username=target_user.username,
        first_name=target_user.first_name,
    )

    # Apply warning
    active_count = await SanctionsExecutor.apply_warn(
        bot=message.bot,
        session=session,
        chat_db=chat_db,
        user_db=user_db,
        reason=reason,
        category="manual_admin_warn",
        message_id=message.reply_to_message.message_id,
    )

    # Record AuditLog
    audit_entry = AuditLog(
        chat_id=chat_id,
        user_id=user_db.id,
        action_type="manual_warn",
        category="manual_admin",
        reason=reason,
        confidence=100.0,
        reviewed_by_admin_id=admin_id,
        raw_message_snippet=(message.reply_to_message.text or "")[:400],
    )
    session.add(audit_entry)
    await session.commit()

    admin_name = admin_user.first_name if admin_user else f"Admin {admin_id}"
    target_name = target_user.first_name or f"ID {target_user.id}"

    text = (
        "⚠️ <b>Выдано предупреждение</b>\n\n"
        f"• <b>Пользователь:</b> {target_name} (ID: <code>{target_user.id}</code>)\n"
        f"• <b>Администратор:</b> {admin_name}\n"
        f"• <b>Причина:</b> {reason}\n"
        f"• <b>Предупреждений:</b> <code>{active_count} / {chat_db.warn_limit}</code>\n"
        f"• <b>Срок действия:</b> {chat_db.warn_expiration_days} дней"
    )
    await message.reply(
        text=text,
        reply_markup=get_group_moderation_keyboard(chat_id, target_user.id, audit_entry.id),
    )


@router.message(Command("unwarn"))
async def handle_manual_unwarn_command(message: Message, session: AsyncSession) -> None:
    """Remove latest active warning for user in reply."""
    if message.chat.id > 0:
        return

    chat_id = message.chat.id
    admin_id = message.from_user.id if message.from_user else 0

    res_c = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = res_c.scalar_one_or_none()
    if not await is_chat_admin(message.bot, chat_id, admin_id, chat_db):
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply("Ответьте командой <code>/unwarn</code> на сообщение пользователя, чтобы снять варн.")
        return

    target_user = message.reply_to_message.from_user
    res_u = await session.execute(
        select(User).where(User.chat_id == chat_id, User.telegram_id == target_user.id)
    )
    user_db = res_u.scalar_one_or_none()
    if not user_db:
        await message.reply("У этого пользователя нет предупреждений.")
        return

    # Deactivate latest warn
    res_w = await session.execute(
        select(Warn)
        .where(Warn.user_id == user_db.id, Warn.chat_id == chat_id, Warn.is_active == True)  # noqa: E712
        .order_by(Warn.id.desc())
    )
    latest_warn = res_w.scalars().first()
    if not latest_warn:
        await message.reply("У этого пользователя нет активных предупреждений.")
        return

    latest_warn.is_active = False
    user_db.reputation_score = min(100, user_db.reputation_score + 15)
    await session.commit()

    admin_name = message.from_user.first_name if message.from_user else "Admin"
    await message.reply(f"✅ Предупреждение для {target_user.first_name} успешно снято администратором {admin_name}.")


@router.message(Command("clearwarns"))
async def handle_clear_warns_command(message: Message, session: AsyncSession) -> None:
    """Clear all active warnings for user."""
    if message.chat.id > 0:
        return

    chat_id = message.chat.id
    admin_id = message.from_user.id if message.from_user else 0

    res_c = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = res_c.scalar_one_or_none()
    if not await is_chat_admin(message.bot, chat_id, admin_id, chat_db):
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply("Ответьте командой <code>/clearwarns</code> на сообщение пользователя.")
        return

    target_user = message.reply_to_message.from_user
    res_u = await session.execute(
        select(User).where(User.chat_id == chat_id, User.telegram_id == target_user.id)
    )
    user_db = res_u.scalar_one_or_none()
    if not user_db:
        await message.reply("У пользователя нет истории предупреждений.")
        return

    res_w = await session.execute(
        select(Warn).where(Warn.user_id == user_db.id, Warn.chat_id == chat_id, Warn.is_active == True)  # noqa: E712
    )
    warns = res_w.scalars().all()
    for w in warns:
        w.is_active = False

    user_db.reputation_score = 100
    await session.commit()
    await message.reply(f"✅ Все активные предупреждения ({len(warns)}) для {target_user.first_name} успешно очищены!")


@router.message(Command("mute"))
async def handle_manual_mute_command(message: Message, session: AsyncSession) -> None:
    """Mute user for specified duration (/mute 30m [причина])."""
    if message.chat.id > 0:
        return

    chat_id = message.chat.id
    admin_id = message.from_user.id if message.from_user else 0

    res_c = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = res_c.scalar_one_or_none()
    if not await is_chat_admin(message.bot, chat_id, admin_id, chat_db):
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply("Ответьте командой <code>/mute &lt;время, напр. 30m, 2h, 1d&gt; [причина]</code> на сообщение нарушителя.")
        return

    target_user = message.reply_to_message.from_user
    if target_user.is_bot or await is_chat_admin(message.bot, chat_id, target_user.id, chat_db):
        await message.reply("Нельзя ограничить этого пользователя.")
        return

    args = (message.text or "").split(maxsplit=2)
    duration_minutes = 60  # Default 1 hour
    reason = "Решение администратора"

    if len(args) > 1:
        parsed = parse_duration_string(args[1])
        if parsed:
            duration_minutes = parsed
            if len(args) > 2:
                reason = args[2]
        else:
            reason = " ".join(args[1:])

    user_db = await SanctionsExecutor.get_or_create_user(
        session=session,
        chat_id=chat_id,
        telegram_id=target_user.id,
        username=target_user.username,
        first_name=target_user.first_name,
    )

    await SanctionsExecutor.mute_user(
        bot=message.bot,
        session=session,
        chat_id=chat_id,
        user_db=user_db,
        duration_minutes=duration_minutes,
        reason=reason,
    )
    await session.commit()

    admin_name = message.from_user.first_name if message.from_user else "Admin"
    await message.reply(
        f"🔇 <b>Пользователь {target_user.first_name} отправлен в мут</b>\n\n"
        f"• <b>Длительность:</b> {duration_minutes} мин.\n"
        f"• <b>Причина:</b> {reason}\n"
        f"• <b>Администратор:</b> {admin_name}"
    )


@router.message(Command("unmute"))
async def handle_manual_unmute_command(message: Message, session: AsyncSession) -> None:
    """Unmute user in reply."""
    if message.chat.id > 0:
        return

    chat_id = message.chat.id
    admin_id = message.from_user.id if message.from_user else 0

    res_c = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = res_c.scalar_one_or_none()
    if not await is_chat_admin(message.bot, chat_id, admin_id, chat_db):
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply("Ответьте командой <code>/unmute</code> на сообщение пользователя.")
        return

    target_user = message.reply_to_message.from_user
    try:
        from bot.handlers.admin_actions import UNRESTRICTED_PERMISSIONS
        await message.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=target_user.id,
            permissions=UNRESTRICTED_PERMISSIONS,
        )
        res_u = await session.execute(
            select(User).where(User.chat_id == chat_id, User.telegram_id == target_user.id)
        )
        user_db = res_u.scalar_one_or_none()
        if user_db:
            user_db.is_muted = False
            user_db.muted_until = None
            await session.commit()

        await message.reply(f"🔊 Пользователь {target_user.first_name} успешно размучен!")
    except Exception as err:
        logger.error(f"Failed to unmute user: {err}")
        await message.reply("Ошибка при снятии мута.")


@router.message(Command("ban"))
async def handle_manual_ban_command(message: Message, session: AsyncSession) -> None:
    """Ban user in reply (/ban [причина])."""
    if message.chat.id > 0:
        return

    chat_id = message.chat.id
    admin_id = message.from_user.id if message.from_user else 0

    res_c = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = res_c.scalar_one_or_none()
    if not await is_chat_admin(message.bot, chat_id, admin_id, chat_db):
        return

    if not message.reply_to_message or not message.reply_to_message.from_user:
        await message.reply("Ответьте командой <code>/ban [причина]</code> на сообщение нарушителя.")
        return

    target_user = message.reply_to_message.from_user
    if target_user.is_bot or await is_chat_admin(message.bot, chat_id, target_user.id, chat_db):
        await message.reply("Нельзя заблокировать этого пользователя.")
        return

    parts = (message.text or "").split(maxsplit=1)
    reason = parts[1] if len(parts) > 1 else "Решение администратора"

    user_db = await SanctionsExecutor.get_or_create_user(
        session=session,
        chat_id=chat_id,
        telegram_id=target_user.id,
        username=target_user.username,
        first_name=target_user.first_name,
    )

    await SanctionsExecutor.ban_user(
        bot=message.bot,
        session=session,
        chat_id=chat_id,
        user_db=user_db,
        reason=reason,
    )
    await session.commit()

    admin_name = message.from_user.first_name if message.from_user else "Admin"
    await message.reply(
        f"⛔ <b>Пользователь {target_user.first_name} заблокирован</b>\n\n"
        f"• <b>Причина:</b> {reason}\n"
        f"• <b>Администратор:</b> {admin_name}"
    )


@router.message(Command("settings"))
async def handle_in_chat_settings_command(message: Message, session: AsyncSession) -> None:
    """Send settings button and link for chat admins."""
    if message.chat.id > 0:
        return

    chat_id = message.chat.id
    admin_id = message.from_user.id if message.from_user else 0

    res_c = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = res_c.scalar_one_or_none()
    if not await is_chat_admin(message.bot, chat_id, admin_id, chat_db):
        return

    bot_info = await message.bot.get_me()
    username = bot_info.username or "TelegramWardenBot"
    webapp_url = settings.WEBAPP_URL or ""

    kb_buttons = []
    if webapp_url:
        from aiogram.types import WebAppInfo
        kb_buttons.append([
            InlineKeyboardButton(text="⚡ Открыть панель настроек", web_app=WebAppInfo(url=webapp_url))
        ])
    kb_buttons.append([
        InlineKeyboardButton(text="💬 Личные сообщения бота", url=f"https://t.me/{username}?start=settings_{abs(chat_id)}")
    ])

    await message.reply(
        "<b>⚙️ Настройки модерации сообщества</b>\n\n"
        "Нажмите кнопку ниже, чтобы открыть веб-панель управления фильтрами и правилами:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons),
    )


# ==========================================
# Report action callbacks
# ==========================================

@router.callback_query(F.data.startswith("rep:del:"))
async def handle_report_delete_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    """Delete message flagged by report."""
    parts = callback.data.split(":")
    if len(parts) != 4:
        return
    chat_id = int(parts[2])
    msg_id = int(parts[3])
    admin_id = callback.from_user.id

    res_c = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = res_c.scalar_one_or_none()
    if not await is_chat_admin(callback.bot, chat_id, admin_id, chat_db):
        await callback.answer("Только администраторы могут совершать это действие.", show_alert=True)
        return

    await SanctionsExecutor.delete_message(callback.bot, chat_id, msg_id)
    admin_name = callback.from_user.first_name or f"Admin {admin_id}"
    await callback.message.edit_text(f"🗑️ Сообщение удалено администратором {admin_name}.")
    await callback.answer("Сообщение удалено!")


@router.callback_query(F.data.startswith("rep:warn:"))
async def handle_report_warn_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    """Warn user flagged by report."""
    parts = callback.data.split(":")
    if len(parts) != 4:
        return
    chat_id = int(parts[2])
    target_id = int(parts[3])
    admin_id = callback.from_user.id

    res_c = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = res_c.scalar_one_or_none()
    if not await is_chat_admin(callback.bot, chat_id, admin_id, chat_db):
        await callback.answer("Только администраторы могут совершать это действие.", show_alert=True)
        return

    user_db = await SanctionsExecutor.get_or_create_user(session, chat_id, target_id)
    active_count = await SanctionsExecutor.apply_warn(
        bot=callback.bot,
        session=session,
        chat_db=chat_db,
        user_db=user_db,
        reason="Варн по жалобе участников",
        category="manual_admin_warn",
    )
    await session.commit()

    admin_name = callback.from_user.first_name or f"Admin {admin_id}"
    await callback.message.edit_text(f"⚠️ Пользователю {target_id} выдан варн ({active_count}/{chat_db.warn_limit}) администратором {admin_name}.")
    await callback.answer("Варн выдан!")


@router.callback_query(F.data.startswith("rep:ban:"))
async def handle_report_ban_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    """Ban user flagged by report."""
    parts = callback.data.split(":")
    if len(parts) != 4:
        return
    chat_id = int(parts[2])
    target_id = int(parts[3])
    admin_id = callback.from_user.id

    res_c = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = res_c.scalar_one_or_none()
    if not await is_chat_admin(callback.bot, chat_id, admin_id, chat_db):
        await callback.answer("Только администраторы могут совершать это действие.", show_alert=True)
        return

    res_u = await session.execute(
        select(User).where(User.chat_id == chat_id, User.telegram_id == target_id)
    )
    user_db = res_u.scalar_one_or_none()
    if user_db:
        await SanctionsExecutor.ban_user(callback.bot, session, chat_id, user_db, reason="Бан по жалобе участников")
        await session.commit()

    admin_name = callback.from_user.first_name or f"Admin {admin_id}"
    await callback.message.edit_text(f"⛔ Пользователь {target_id} забанен администратором {admin_name}.")
    await callback.answer("Пользователь забанен!")

