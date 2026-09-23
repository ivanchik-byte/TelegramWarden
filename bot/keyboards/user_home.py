"""Home menu keyboard for regular users."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def get_user_home_keyboard(bot_username: str, is_admin: bool = False, webapp_url: str = "") -> InlineKeyboardMarkup:
    """Generate main interactive home menu keyboard for users."""
    buttons = [
        [
            InlineKeyboardButton(text=" Мой профиль", callback_data="user:profile"),
            InlineKeyboardButton(text=" Мои предупреждения", callback_data="user:warns"),
        ],
        [
            InlineKeyboardButton(text=" Правила и безопасность", callback_data="user:rules"),
            InlineKeyboardButton(text=" Команды бота", callback_data="user:help"),
        ],
        [
            InlineKeyboardButton(
                text=" Добавить бота в группу",
                url=f"https://t.me/{bot_username}?startgroup=true&admin=change_info+delete_messages+restrict_members+invite_users+pin_messages",
            ),
        ],
    ]
    if is_admin and webapp_url:
        buttons.insert(0, [
            InlineKeyboardButton(
                text=" Открыть панель управления",
                web_app=WebAppInfo(url=webapp_url),
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
