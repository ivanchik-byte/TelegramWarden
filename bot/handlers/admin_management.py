"""Admin management router: dynamic whitelist and administrator control via bot commands."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.admin_checker import is_chat_admin, is_superadmin
from core.config import settings
from core.logger import logger
from models import Chat

router = Router(name="admin_management")


@router.message(Command("admin"))
async def handle_admin_command(message: Message, session: AsyncSession) -> None:
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0

    # 1. If in group chat, delete user command to keep group clean
    if chat_id < 0:
        try:
            await message.delete()
        except Exception:
            pass

    # 2. Fetch chat settings
    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()

    if not chat_db:
        chat_db = Chat(chat_id=chat_id, title=message.chat.title or "Chat")
        session.add(chat_db)
        await session.flush()

    # 3. Check caller permissions
    has_rights = await is_chat_admin(message.bot, chat_id, user_id, chat_db)
    if not has_rights:
        if chat_id > 0:
            await message.reply("У вас нет прав для управления администраторами.")
        return

    # 3. Parse command arguments: /admin add <id>, /admin remove <id>, /admin list
    args = (message.text or "").split()
    if len(args) < 2 or args[1] == "list":
        whitelist = chat_db.whitelisted_users or []
        superadmins = settings.superadmin_id_list
        text = (
            "<b>Управление доверенными пользователями и админами:</b>\n\n"
            f"<b>Глобальные супер-админы (.env):</b>\n<code>{', '.join(map(str, superadmins)) or 'Не заданы'}</code>\n\n"
            f"<b>Белый список чата ({len(whitelist)}):</b>\n<code>{', '.join(map(str, whitelist)) or 'Пуст'}</code>\n\n"
            "<b>Команды управления:</b>\n"
            "• <code>/admin add &lt;ID&gt;</code> — добавить пользователя в белый список\n"
            "• <code>/admin remove &lt;ID&gt;</code> — удалить из белого списка\n"
            "• <code>/admin list</code> — показать текущий список"
        )
        await message.reply(text=text)
        return

    action = args[1].lower()

    if action == "add":
        if len(args) < 3:
            await message.reply("Укажите числовой Telegram ID: <code>/admin add 123456789</code>")
            return
        target_id_str = args[2].replace("@", "")
        if not target_id_str.lstrip("-").isdigit():
            await message.reply("ID должен быть числом.")
            return

        target_id = int(target_id_str)
        current_list = list(chat_db.whitelisted_users or [])
        if target_id not in current_list:
            current_list.append(target_id)
            chat_db.whitelisted_users = current_list
            await session.commit()
            await message.reply(f"Пользователь <code>{target_id}</code> успешно добавлен в белый список чата!")
            logger.info(f"Admin {user_id} added {target_id} to whitelist in chat {chat_id}")
        else:
            await message.reply(f"Пользователь <code>{target_id}</code> уже находится в белом списке.")

    elif action == "remove":
        if len(args) < 3:
            await message.reply("Укажите числовой Telegram ID: <code>/admin remove 123456789</code>")
            return
        target_id_str = args[2].replace("@", "")
        if not target_id_str.lstrip("-").isdigit():
            await message.reply("ID должен быть числом.")
            return

        target_id = int(target_id_str)
        current_list = list(chat_db.whitelisted_users or [])
        if target_id in current_list:
            current_list.remove(target_id)
            chat_db.whitelisted_users = current_list
            await session.commit()
            await message.reply(f"Пользователь <code>{target_id}</code> удален из белого списка.")
            logger.info(f"Admin {user_id} removed {target_id} from whitelist in chat {chat_id}")
        else:
            await message.reply(f"Пользователь <code>{target_id}</code> не найден в белом списке.")
    else:
        await message.reply("Неизвестное действие. Доступно: <code>add</code>, <code>remove</code>, <code>list</code>.")
