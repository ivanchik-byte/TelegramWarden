"""Inline keyboards for interactive admin audit log cards and group moderation notices."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_group_moderation_keyboard(
    chat_id: int,
    user_id: int,
    log_id: int,
) -> InlineKeyboardMarkup:
    """Generate moderation notice keyboard with appeal button for group chat."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Не согласен (Апелляция)",
                    callback_data=f"appeal:open:{chat_id}:{user_id}:{log_id}",
                )
            ]
        ]
    )


def get_admin_appeal_review_keyboard(
    chat_id: int,
    user_id: int,
    log_id: int,
) -> InlineKeyboardMarkup:
    """Generate review buttons for admins when an appeal is submitted."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Разбанить / Снять варн",
                    callback_data=f"appeal:accept:{chat_id}:{user_id}:{log_id}",
                ),
                InlineKeyboardButton(
                    text="Отклонить апелляцию",
                    callback_data=f"appeal:reject:{chat_id}:{user_id}:{log_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Ложное срабатывание ИИ",
                    callback_data=f"log:false_pos:{log_id}",
                )
            ],
        ]
    )


def get_admin_log_keyboard(
    chat_id: int,
    user_id: int,
    log_id: int,
    is_ban_action: bool = False,
) -> InlineKeyboardMarkup:
    """Generate action buttons for admin audit log verification card."""
    if is_ban_action:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Разбанить",
                        callback_data=f"log:unban:{chat_id}:{user_id}:{log_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="Ложное срабатывание",
                        callback_data=f"log:false_pos:{log_id}",
                    ),
                ],
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Снять варн",
                    callback_data=f"log:unwarn:{chat_id}:{user_id}:{log_id}",
                ),
                InlineKeyboardButton(
                    text="Забанить навсегда",
                    callback_data=f"log:ban:{chat_id}:{user_id}:{log_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Ложное срабатывание",
                    callback_data=f"log:false_pos:{log_id}",
                ),
            ],
        ]
    )


