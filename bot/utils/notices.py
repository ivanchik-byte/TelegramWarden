"""Shared moderation notification cards for group notices and admin review."""

from aiogram import Bot

from html import escape as quote

from core.logger import logger
from bot.keyboards.admin_logs import get_admin_log_keyboard, get_group_moderation_keyboard


async def send_group_moderation_notice(
    bot: Bot,
    chat_id: int,
    user_name: str,
    user_id: int,
    action_title: str,
    category: str,
    confidence: float,
    reason: str,
    audit_entry_id: int,
) -> None:
    """Post the public moderation card with an appeal button to the group."""
    notice_text = (
        "<b>TelegramWarden | Модерация</b>\n\n"
        f"• <b>Пользователь:</b> {quote(user_name)} (ID: <code>{user_id}</code>)\n"
        f"• <b>Действие:</b> <code>{quote(action_title)}</code>\n"
        f"• <b>Причина:</b> {quote(category)} ({round(confidence)}%)\n"
        f"• <b>Пояснение:</b> {quote(reason)}\n\n"
        "<i>Если вы не согласны с решением, нажмите кнопку ниже для подачи апелляции:</i>"
    )
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=notice_text,
            reply_markup=get_group_moderation_keyboard(chat_id, user_id, audit_entry_id),
        )
    except Exception as err:
        logger.warning(f"Failed to post group moderation notice in {chat_id}: {err}")


async def send_admin_review_card(
    bot: Bot,
    chat_db,  # Chat model
    user_name: str,
    user_id: int,
    message_preview: str,
    category: str,
    confidence: float,
    reason: str,
    audit_entry_id: int,
    is_ban_action: bool = False,
) -> None:
    """Deliver the suspicious-content review card to the log channel.

    Falls back to the group chat itself when no log channel is configured,
    so admin review cards are never silently dropped.
    """
    admin_card_text = (
        " <b>Спорное сообщение на проверку администраторам</b>\n\n"
        f"• <b>Чат:</b> {quote(chat_db.title or str(chat_db.chat_id))}\n"
        f"• <b>От:</b> {quote(user_name)} (ID: <code>{user_id}</code>)\n"
        f"• <b>Содержимое:</b> <i>«{quote(message_preview[:200])}»</i>\n"
        f"• <b>Оценка:</b> {quote(category)} ({int(confidence)}%)\n"
        f"• <b>Причина:</b> {quote(reason)}\n\n"
        "<i>Выберите действие ниже:</i>"
    )

    target = chat_db.log_channel_id if getattr(chat_db, "log_channel_id", None) else chat_db.chat_id
    try:
        await bot.send_message(
            chat_id=target,
            text=admin_card_text,
            reply_markup=get_admin_log_keyboard(
                chat_db.chat_id, user_id, audit_entry_id, is_ban_action=is_ban_action
            ),
        )
    except Exception as err:
        # Broad catch: a card failure must never bubble up and roll back the
        # transaction: sanctions are already applied in Telegram by now
        logger.warning(f"Failed to send admin review card to {target}: {err}")
