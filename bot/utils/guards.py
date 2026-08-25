"""Shared message-source guards against anonymous channels and inline bots."""

from aiogram.types import Message
from core.logger import logger
from models import Chat
from bot.utils.sanctions import SanctionsExecutor


async def enforce_source_guards(message: Message, chat_db: Chat) -> bool:
    """Delete unauthorized channel-spoofed and inline-bot messages.

    Returns True when the message source is allowed and processing may continue.
    """
    chat_id = message.chat.id

    # Anti-Channel protection (sent as channel / anonymously)
    if message.sender_chat:
        sender_channel_id = message.sender_chat.id
        if sender_channel_id != chat_id and not chat_db.allow_sender_chat:
            if sender_channel_id not in (chat_db.whitelisted_channels or []):
                logger.info(f"Unauthorized sender_chat {sender_channel_id} in group {chat_id}. Deleting.")
                await SanctionsExecutor.delete_message(message.bot, chat_id, message.message_id)
                try:
                    await message.bot.ban_chat_sender_chat(chat_id=chat_id, sender_chat_id=sender_channel_id)
                except Exception:
                    pass
                return False

    # Anti-Inline bot protection (via_bot)
    if message.via_bot and not chat_db.allow_via_bot:
        bot_username = f"@{message.via_bot.username}" if message.via_bot.username else ""
        if bot_username not in (chat_db.whitelisted_bots or []):
            logger.info(f"Unauthorized via_bot {bot_username} in {chat_id}. Deleting.")
            await SanctionsExecutor.delete_message(message.bot, chat_id, message.message_id)
            return False

    return True
