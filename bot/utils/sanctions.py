"""Sanctions executor: warnings, mutes, bans, and message deletion."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from aiogram import Bot
from aiogram.types import ChatPermissions
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from core.logger import logger
from models import Chat, User, Warn, AuditLog

MUTE_PERMISSIONS = ChatPermissions(
    can_send_messages=False,
    can_send_media_messages=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
)


class SanctionsExecutor:
    """Applies moderation actions in Telegram and records history in database."""

    @classmethod
    async def delete_message(cls, bot: Bot, chat_id: int, message_id: int) -> bool:
        """Safely delete a message from Telegram chat."""
        try:
            return await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as err:
            logger.debug(f"Failed to delete message {message_id} in {chat_id}: {err}")
            return False

    @classmethod
    async def get_or_create_user(
        cls,
        session: AsyncSession,
        chat_id: int,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: str = "",
    ) -> User:
        """Get existing user record or create new one in permanent data layer."""
        result = await session.execute(
            select(User).where(User.chat_id == chat_id, User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                chat_id=chat_id,
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            )
            session.add(user)
            await session.flush()
        else:
            if username and user.username != username:
                user.username = username
            if first_name and user.first_name != first_name:
                user.first_name = first_name
        return user

    @classmethod
    async def apply_warn(
        cls,
        bot: Bot,
        session: AsyncSession,
        chat_db: Chat,
        user_db: User,
        reason: str,
        category: str = "general",
        message_id: Optional[int] = None,
    ) -> int:
        """Issue a warning and apply punishment if warn limit is reached."""
        now = datetime.now(timezone.utc)

        # 1. Create Warn entry
        warn = Warn(
            user_id=user_db.id,
            chat_id=chat_db.chat_id,
            reason=reason,
            category=category,
            message_id=message_id,
        )
        session.add(warn)
        user_db.total_violations_count += 1
        user_db.reputation_score = max(0, user_db.reputation_score - 15)
        await session.flush()

        # 2. Count active warns
        count_res = await session.execute(
            select(func.count(Warn.id)).where(
                Warn.user_id == user_db.id,
                Warn.chat_id == chat_db.chat_id,
                Warn.is_active == True,  # noqa: E712
                Warn.expires_at > now,
            )
        )
        active_warns_count = count_res.scalar() or 1

        # 3. Check if warn limit is exceeded
        if active_warns_count >= chat_db.warn_limit:
            logger.info(f"User {user_db.telegram_id} reached warn limit ({active_warns_count}/{chat_db.warn_limit})")

            # Deactivate used warns
            warns_to_deactivate = await session.execute(
                select(Warn).where(Warn.user_id == user_db.id, Warn.chat_id == chat_db.chat_id)
            )
            for w in warns_to_deactivate.scalars():
                w.is_active = False

            if chat_db.warn_punishment == "ban":
                await cls.ban_user(bot, session, chat_db.chat_id, user_db, reason="Превышен лимит предупреждений")
            else:
                # Default: Mute for configured duration
                duration = chat_db.warn_mute_duration_minutes
                await cls.mute_user(
                    bot=bot,
                    session=session,
                    chat_id=chat_db.chat_id,
                    user_db=user_db,
                    duration_minutes=duration,
                    reason=f"Превышен лимит предупреждений ({chat_db.warn_limit}/{chat_db.warn_limit})",
                )
        else:
            # Notify in chat with clean Russian text (no emojis)
            try:
                name = user_db.first_name or f"User {user_db.telegram_id}"
                await bot.send_message(
                    chat_id=chat_db.chat_id,
                    text=f"Предупреждение для {name} [{active_warns_count}/{chat_db.warn_limit}]. Причина: {reason}",
                )
            except Exception as notify_err:
                logger.debug(f"Failed to send warn notification: {notify_err}")

        return active_warns_count

    @classmethod
    async def mute_user(
        cls,
        bot: Bot,
        session: AsyncSession,
        chat_id: int,
        user_db: User,
        duration_minutes: int,
        reason: str,
    ) -> bool:
        """Mute user in Telegram and update database status."""
        until_date = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        try:
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_db.telegram_id,
                permissions=MUTE_PERMISSIONS,
                until_date=until_date,
            )
            user_db.is_muted = True
            user_db.muted_until = until_date
            await session.flush()

            name = user_db.first_name or f"User {user_db.telegram_id}"
            await bot.send_message(
                chat_id=chat_id,
                text=f"Пользователь {name} ограничен в отправке сообщений на {duration_minutes} минут. Причина: {reason}",
            )
            return True
        except Exception as err:
            logger.error(f"Failed to mute user {user_db.telegram_id}: {err}")
            return False

    @classmethod
    async def ban_user(
        cls,
        bot: Bot,
        session: AsyncSession,
        chat_id: int,
        user_db: User,
        reason: str,
        revoke_messages: bool = True,
    ) -> bool:
        """Ban user from Telegram chat and record permanent ban status."""
        try:
            await bot.ban_chat_member(
                chat_id=chat_id,
                user_id=user_db.telegram_id,
                revoke_messages=revoke_messages,
            )
            user_db.is_banned = True
            user_db.ban_reason = reason
            user_db.banned_at = datetime.now(timezone.utc)
            await session.flush()

            name = user_db.first_name or f"User {user_db.telegram_id}"
            await bot.send_message(
                chat_id=chat_id,
                text=f"Пользователь {name} заблокирован. Причина: {reason}",
            )
            return True
        except Exception as err:
            logger.error(f"Failed to ban user {user_db.telegram_id}: {err}")
            return False
