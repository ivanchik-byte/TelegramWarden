"""Start command with role-based routing to admin panel or user home."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import (
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.admin_panel import get_admin_main_menu_keyboard
from bot.keyboards.user_home import get_user_home_keyboard
from bot.utils.admin_checker import get_user_administered_chats, is_superadmin
from core.config import settings

router = Router(name="start_help")


@router.message(CommandStart())
async def handle_start_command(message: Message, session: AsyncSession) -> None:
    """Handle /start command with strict role-based access control."""
    bot_info = await message.bot.get_me()
    username = bot_info.username or "telegrahgwarden_bot"
    user_id = message.from_user.id if message.from_user else 0

    # 1. Group Chat: Keep group 100% clean
    if message.chat.id < 0:
        try:
            await message.delete()
        except Exception:
            pass
        return

    # 2. Private Chat: Verify administrative permissions
    accessible_chats = await get_user_administered_chats(message.bot, session, user_id)

    # If user has no admin groups and is not a superadmin -> Show User Profile & Menu
    if not accessible_chats and not is_superadmin(user_id):
        user_name = message.from_user.first_name if message.from_user else "Пользователь"
        text = (
            f" <b>Здравствуйте, {user_name}!</b>\n\n"
            "<b>TelegramWarden</b> — это система интеллектуальной защиты и модерации чатов.\n\n"
            "Здесь вы можете посмотреть свой личный профиль, статус предупреждений в группах и ознакомиться с правилами безопасности."
        )
        keyboard = get_user_home_keyboard(username, is_admin=False, webapp_url="")
        await message.reply(text=text, reply_markup=keyboard)
        return


    # User is Admin or SuperAdmin -> Open Admin Command Center
    webapp_url = settings.WEBAPP_URL or ""
    if webapp_url and webapp_url.startswith("https://") and "localhost" not in webapp_url:
        try:
            await message.bot.set_chat_menu_button(
                chat_id=message.chat.id,
                menu_button=MenuButtonWebApp(
                    text="Панель управления",
                    web_app=WebAppInfo(url=webapp_url),
                ),
            )
        except Exception:
            pass

    active_model = settings.DEEPSEEK_MODEL or "meta/llama-3.1-8b-instruct"
    text = (
        "<b>Панель управления TelegramWarden</b>\n\n"
        "Вы авторизованы как <b>Администратор</b>.\n"
        f"• Доступных групп: <b>{len(accessible_chats)}</b>\n"
        f"• ИИ-Движок: <b>Онлайн (NVIDIA NIM • <code>{active_model}</code>)</b>\n"
        "• Локальный медиа-фильтр: <b>0 токенов на CPU (NudeNet v3)</b>\n\n"
        "Выберите группу для настройки или воспользуйтесь меню ниже:"
    )
    keyboard = get_admin_main_menu_keyboard(accessible_chats, username, webapp_url)
    await message.reply(text=text, reply_markup=keyboard)


