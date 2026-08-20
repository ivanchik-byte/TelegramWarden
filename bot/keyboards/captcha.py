"""Inline keyboards for newcomer verification and captcha."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_captcha_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Generate verification inline keyboard with Russian label."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Я человек",
                    callback_data=f"captcha:verify:{user_id}",
                )
            ]
        ]
    )
