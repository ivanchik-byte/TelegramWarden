"""Message moderation handler for text, forwards, channels, and inline bots."""

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.guards import enforce_source_guards
from bot.utils.sanctions import SanctionsExecutor
from bot.utils.text_moderation import moderate_text_content
from core.logger import logger
from models import Chat

router = Router(name="text_moderation")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_message(message: Message, session: AsyncSession) -> None:
    """Analyze incoming text message against security policies and AI intent engine."""
    chat_id = message.chat.id
    if chat_id > 0:
        # groups only; private bot chats route to start/settings dashboard
        return

    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()
    if not chat_db:
        chat_db = Chat(chat_id=chat_id, title=message.chat.title or "Group")
        session.add(chat_db)
        await session.flush()

    if not chat_db.is_active:
        return

    if not await enforce_source_guards(message, chat_db):
        return

    if not message.from_user:
        return

    user_id = message.from_user.id
    if user_id in (chat_db.whitelisted_users or []):
        # whitelist grants moderation exemption only, source guards above still apply
        return

    user_db = await SanctionsExecutor.get_or_create_user(
        session=session,
        chat_id=chat_id,
        telegram_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    # lock row before incrementing message_count to prevent lost updates under concurrent messages
    await SanctionsExecutor.lock_user(session, user_db)
    user_db.message_count += 1

    await moderate_text_content(
        bot=message.bot,
        session=session,
        message=message,
        chat_db=chat_db,
        user_db=user_db,
        raw_text=message.text or "",
    )
