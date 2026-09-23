"""Admin and role-based access verification utilities."""

import asyncio
import json
from typing import Optional
from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import settings
from core.logger import logger
from core.redis_client import redis_manager
from models import Chat

# Admin panel entries fan out one get_chat_member per chat: cache the
# resulting chat list briefly instead of hammering Telegram on every open.
ADMIN_CHATS_CACHE_TTL = 300


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
    cache_key = f"warden:admin_chats:{user_id}"
    try:
        redis = await redis_manager.get_client()
        cached = await redis.get(cache_key)
        if cached:
            ids = set(json.loads(cached))
            result = await session.execute(select(Chat).where(Chat.chat_id.in_(ids)))
            return list(result.scalars().all())
    except Exception as err:
        logger.debug(f"Admin chats cache miss for {user_id}: {err}")

    result = await session.execute(select(Chat))
    all_chats = result.scalars().all()

    if not all_chats:
        return []

    # Superadmins have access to all registered groups
    if is_superadmin(user_id):
        return list(all_chats)

    semaphore = asyncio.Semaphore(5)

    async def _is_admin(chat_db: Chat) -> Optional[Chat]:
        async with semaphore:
            try:
                member = await bot.get_chat_member(chat_id=chat_db.chat_id, user_id=user_id)
                if member.status in ("creator", "administrator"):
                    return chat_db
            except Exception:
                pass
        return None

    checked = await asyncio.gather(*(_is_admin(chat_db) for chat_db in all_chats))
    administered = [chat_db for chat_db in checked if chat_db is not None]
    try:
        redis = await redis_manager.get_client()
        await redis.set(
            cache_key, json.dumps([c.chat_id for c in administered]), ex=ADMIN_CHATS_CACHE_TTL
        )
    except Exception as err:
        logger.debug(f"Admin chats cache store failed for {user_id}: {err}")
    return administered
