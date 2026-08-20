"""Handlers for automatic cleanup of service notifications."""

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.logger import logger
from models import Chat

router = Router(name="service_cleanup")


@router.message(
    F.new_chat_members
    | F.left_chat_member
    | F.pinned_message
    | F.forum_topic_created
    | F.forum_topic_edited
    | F.forum_topic_closed
    | F.forum_topic_reopened
)
async def handle_service_message_cleanup(message: Message, session: AsyncSession) -> None:
    """Delete service messages if clean_service_messages is enabled for the chat."""
    chat_id = message.chat.id
    try:
        result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
        chat_db = result.scalar_one_or_none()

        if chat_db and chat_db.clean_service_messages:
            await message.delete()
            logger.debug(f"Deleted service message {message.message_id} in chat {chat_id}")
    except Exception as err:
        logger.debug(f"Failed to delete service message: {err}")
