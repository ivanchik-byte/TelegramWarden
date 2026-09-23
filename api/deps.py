"""Shared access checks for the Mini App API."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import TelegramUser
from core.config import settings
from models import Chat


def is_superadmin(user_id: int) -> bool:
    return user_id in settings.superadmin_id_list


def can_access_chat(user_id: int, whitelisted: list[int] | None) -> bool:
    return is_superadmin(user_id) or user_id in (whitelisted or [])


def require_superadmin(user: TelegramUser) -> None:
    if not is_superadmin(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: restricted to SuperAdmins",
        )


async def verify_chat_access(chat_id: int, user_id: int, session: AsyncSession) -> None:
    # 403 on missing chat on purpose: never reveal which chat_ids exist.
    # WebApp access is an explicit grant (whitelisted_users), revoked by a
    # superadmin editing the list — not a live Telegram admin status, the API
    # has no Bot instance to call get_chat_member with.
    if is_superadmin(user_id):
        return
    chat_db = (
        (await session.execute(select(Chat).where(Chat.chat_id == chat_id)))
        .scalar_one_or_none()
    )
    if not chat_db or not can_access_chat(user_id, chat_db.whitelisted_users):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not have permission for this chat",
        )
