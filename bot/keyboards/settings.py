"""Inline keyboards for chat settings management in bot direct messages."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from models import Chat


def get_chat_settings_keyboard(chat_db: Chat) -> InlineKeyboardMarkup:
    """Generate toggle buttons for group moderation settings."""
    chat_id = chat_db.chat_id

    captcha_state = "ВКЛ" if chat_db.captcha_enabled else "ВЫКЛ"
    channels_state = "ЗАПРЕЩЕНЫ" if not chat_db.allow_sender_chat else "РАЗРЕШЕНЫ"
    service_state = "УДАЛЯТЬ" if chat_db.clean_service_messages else "ОСТАВЛЯТЬ"
    ai_state = "ВКЛ" if chat_db.ai_moderation_enabled else "ВЫКЛ"
    night_state = "ВКЛ" if chat_db.night_mode_enabled else "ВЫКЛ"

    buttons = [
        [
            InlineKeyboardButton(
                text=f"Капча новичков: [{captcha_state}]",
                callback_data=f"set:tgl:captcha:{chat_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"Отправка от каналов: [{channels_state}]",
                callback_data=f"set:tgl:channels:{chat_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"Служебные сообщения: [{service_state}]",
                callback_data=f"set:tgl:service:{chat_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"ИИ-фильтр спама: [{ai_state}]",
                callback_data=f"set:tgl:ai:{chat_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"Ночной режим: [{night_state}]",
                callback_data=f"set:tgl:night:{chat_id}",
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)
