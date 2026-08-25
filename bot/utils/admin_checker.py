"""Admin and role-based access verification utilities."""

from typing import Optional
from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import settings
from core.logger import logger
from models import Chat


def is_superadmin(user_id: int) -> bool:
    """Check if user is listed in SUPERADMIN_IDS from environment."""
    return user_id in settings.superadmin_id_list


def is_moderation_exempt(user_id: int, chat_db: Optional[Chat]) -> bool:
    """Check if the user's messages skip moderation entirely.

    Being exempt from moderation is NOT a moderation privilege: whitelisted
    members gain nothing beyond immunity of their own messages.
    """
    if is_superadmin(user_id):
        return True
    return bool(chat_db and chat_db.whitelisted_users and user_id in chat_db.whitelisted_users)


async def is_chat_admin(
    bot: Bot,
    chat_id: int,
    user_id: int,
    chat_db: Optional[Chat] = None,
) -> bool:
    """Verify if user has administrative rights over a specific chat.

    Only global superadmins and Telegram-native chat administrators may
    moderate. Chat whitelist membership deliberately grants no privileges.
    """
    # 1. Superadmin global bypass from .env
    if is_superadmin(user_id):
        return True

    # 2. Direct Telegram chat member status check
    if chat_id < 0:
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if member.status in ("creator", "administrator"):
                return True
        except Exception as err:
            logger.debug(f"Failed to check admin status for {user_id} in {chat_id}: {err}")

    return False


async def get_user_administered_chats(
    bot: Bot,
    session: AsyncSession,
    user_id: int,
) -> list[Chat]:
    """Retrieve all chats where the user has administrative privileges."""
    result = await session.execute(select(Chat))
    all_chats = result.scalars().all()

    if not all_chats:
        return []

    # Superadmins have access to all registered groups
    if is_superadmin(user_id):
        return list(all_chats)

    accessible_chats = []
    for chat_db in all_chats:
        # Check Telegram chat status (whitelist grants no admin privileges)
        try:
            member = await bot.get_chat_member(chat_id=chat_db.chat_id, user_id=user_id)
            if member.status in ("creator", "administrator"):
                accessible_chats.append(chat_db)
        except Exception:
            pass

    return accessible_chats
