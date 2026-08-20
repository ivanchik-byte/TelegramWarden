"""Chat settings router: redirects users to private PM dashboard to keep groups clean."""

import asyncio
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.admin_checker import is_chat_admin

router = Router(name="chat_settings")


@router.message(Command("settings"))
async def handle_settings_command(message: Message, session: AsyncSession) -> None:
    """Redirect user from group to private PM dashboard."""
    bot_info = await message.bot.get_me()
    username = bot_info.username or "telegrahgwarden_bot"

    if message.chat.id < 0:
        # Group chat: delete command and send self-destructing notice
        try:
            await message.delete()
        except Exception:
            pass

        user_id = message.from_user.id if message.from_user else 0
        has_rights = await is_chat_admin(message.bot, message.chat.id, user_id)

        if not has_rights:
            return

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Открыть панель настроек в ЛС",
                        url=f"https://t.me/{username}?start=chat_{abs(message.chat.id)}",
                    )
                ]
            ]
        )
        temp_msg = await message.answer(
            text="Все настройки безопасности производятся в личных сообщениях бота, чтобы не засорять чат.",
            reply_markup=kb,
        )

        # Auto-delete notice after 20 seconds
        await asyncio.sleep(20)
        try:
            await temp_msg.delete()
        except Exception:
            pass
    else:
        # In DM: redirect to /start command
        from bot.handlers.start import handle_start_command
        await handle_start_command(message, session)
