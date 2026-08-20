"""Join events, CAS spammer detection, and captcha verification handlers."""

from aiogram import F, Router
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import CallbackQuery, ChatMemberUpdated, ChatPermissions
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.captcha import get_captcha_keyboard
from core.logger import logger
from models import Chat, User
from services.gatekeeper.anti_raid import AntiRaidDetector
from services.gatekeeper.captcha_manager import CaptchaManager
from services.reputation.cas import CASClient

router = Router(name="joins_gatekeeper")

# Default restricted permissions for unverified users
RESTRICTED_PERMISSIONS = ChatPermissions(
    can_send_messages=False,
    can_send_media_messages=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
)

# Standard permissions restored after verification
UNRESTRICTED_PERMISSIONS = ChatPermissions(
    can_send_messages=True,
    can_send_media_messages=True,
    can_send_other_messages=True,
    can_add_web_page_previews=True,
)


@router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
async def handle_new_chat_member(event: ChatMemberUpdated, session: AsyncSession) -> None:
    """Handle newcomer join event, run CAS check, and issue captcha challenge."""
    user = event.new_chat_member.user
    chat = event.chat

    # Ignore bots
    if user.is_bot:
        return

    logger.info(f"New user joined chat {chat.id}: {user.id} (@{user.username})")

    # 1. Fetch chat settings from database or create default
    result = await session.execute(select(Chat).where(Chat.chat_id == chat.id))
    chat_db = result.scalar_one_or_none()
    if not chat_db:
        chat_db = Chat(chat_id=chat.id, title=chat.title or "Group")
        session.add(chat_db)
        await session.commit()

    # 2. Check CAS Database if enabled
    if chat_db.cas_check_enabled:
        cas_result = await CASClient.check_user(user.id)
        if cas_result.is_banned:
            logger.warning(f"CAS-banned user {user.id} attempted to join chat {chat.id}. Banning immediately.")
            try:
                await event.bot.ban_chat_member(chat_id=chat.id, user_id=user.id)
                return
            except Exception as err:
                logger.error(f"Failed to ban CAS spammer {user.id}: {err}")

    # 3. Check Anti-Raid Threshold
    if chat_db.anti_raid_enabled:
        raid_status = await AntiRaidDetector.record_join_and_check(chat_id=chat.id)
        if raid_status.lockdown_active:
            logger.warning(f"Raid lockdown active in chat {chat.id}. Restricting newcomer {user.id}.")
            try:
                await event.bot.restrict_chat_member(
                    chat_id=chat.id,
                    user_id=user.id,
                    permissions=RESTRICTED_PERMISSIONS,
                )
                return
            except Exception as err:
                logger.error(f"Failed to restrict user during raid: {err}")

    # 4. Issue Captcha Challenge if enabled
    if chat_db.captcha_enabled:
        try:
            # Restrict newcomer until verified
            await event.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=RESTRICTED_PERMISSIONS,
            )

            # Send verification message with button
            mention_name = user.first_name or "Участник"
            keyboard = get_captcha_keyboard(user.id)
            captcha_msg = await event.bot.send_message(
                chat_id=chat.id,
                text=f"Добро пожаловать, {mention_name}! Для получения доступа к общению подтвердите, что вы человек.",
                reply_markup=keyboard,
            )

            # Store active challenge in Redis
            await CaptchaManager.create_challenge(
                chat_id=chat.id,
                user_id=user.id,
                message_id=captcha_msg.message_id,
                timeout_seconds=chat_db.captcha_timeout_seconds,
            )

        except Exception as err:
            logger.error(f"Failed to issue captcha for user {user.id}: {err}")


@router.callback_query(F.data.startswith("captcha:verify:"))
async def handle_captcha_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    """Handle verification button click."""
    if not callback.message or not callback.data:
        return

    data_parts = callback.data.split(":")
    if len(data_parts) != 3:
        return

    target_user_id = int(data_parts[2])
    clicker_user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    # Ensure only the target user can click their own verification button
    if clicker_user_id != target_user_id:
        await callback.answer(text="Эта кнопка предназначена для другого участника.", show_alert=True)
        return

    # Complete challenge session in Redis
    await CaptchaManager.complete_challenge(chat_id=chat_id, user_id=clicker_user_id)

    # Restore chat permissions in Telegram
    try:
        await callback.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=clicker_user_id,
            permissions=UNRESTRICTED_PERMISSIONS,
        )
    except Exception as err:
        logger.error(f"Failed to restore permissions for user {clicker_user_id}: {err}")

    # Delete the captcha challenge message
    try:
        await callback.message.delete()
    except Exception as err:
        logger.debug(f"Failed to delete captcha message: {err}")

    await callback.answer(text="Верификация успешно пройдена!")
    logger.info(f"User {clicker_user_id} verified successfully in chat {chat_id}")
