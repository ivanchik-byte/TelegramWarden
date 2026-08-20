"""User commands and interactive profile router for regular chat members."""

from datetime import datetime, timezone
from typing import Optional
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.admin_logs import get_admin_log_keyboard
from bot.utils.admin_checker import is_chat_admin, is_superadmin
from core.config import settings
from core.logger import logger
from models import AuditLog, Chat, User, Warn

router = Router(name="user_commands")


def get_user_home_keyboard(bot_username: str, is_admin: bool = False, webapp_url: str = "") -> InlineKeyboardMarkup:
    """Generate main interactive home menu keyboard for users."""
    buttons = [
        [
            InlineKeyboardButton(text="👤 Мой профиль", callback_data="user:profile"),
            InlineKeyboardButton(text="📋 Мои предупреждения", callback_data="user:warns"),
        ],
        [
            InlineKeyboardButton(text="📖 Правила и безопасность", callback_data="user:rules"),
            InlineKeyboardButton(text="❓ Команды бота", callback_data="user:help"),
        ],
        [
            InlineKeyboardButton(
                text="➕ Добавить бота в группу",
                url=f"https://t.me/{bot_username}?startgroup=true&admin=change_info+delete_messages+restrict_members+invite_users+pin_messages",
            ),
        ],
    ]
    if is_admin and webapp_url:
        from aiogram.types import WebAppInfo
        buttons.insert(0, [
            InlineKeyboardButton(
                text="⚡ Открыть панель управления",
                web_app=WebAppInfo(url=webapp_url),
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "user:home")
async def handle_user_home_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    """Return to user main home menu."""
    if not callback.message:
        return
    bot_info = await callback.bot.get_me()
    username = bot_info.username or "TelegramWardenBot"
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name or "Пользователь"

    text = (
        f"<b>Здравствуйте, {user_name}!</b>\n\n"
        "<b>TelegramWarden</b> — это система интеллектуальной защиты и модерации чатов.\n\n"
        "Здесь вы можете посмотреть свой профиль, проверить статус предупреждений в группах и ознакомиться с правилами безопасности."
    )
    is_admin = is_superadmin(user_id)
    await callback.message.edit_text(
        text=text,
        reply_markup=get_user_home_keyboard(username, is_admin=is_admin, webapp_url=settings.WEBAPP_URL or ""),
    )
    await callback.answer()


@router.callback_query(F.data == "user:profile")
async def handle_user_profile_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show detailed user reputation profile across protected chats."""
    if not callback.message:
        return
    user_id = callback.from_user.id
    user_name = callback.from_user.full_name or "Пользователь"
    username_str = f"@{callback.from_user.username}" if callback.from_user.username else "Не задан"
    now = datetime.now(timezone.utc)

    # Aggregate violations and active warns across all chats
    res_stats = await session.execute(
        select(
            func.count(User.id),
            func.coalesce(func.sum(User.total_violations_count), 0),
            func.coalesce(func.avg(User.reputation_score), 100.0),
        ).where(User.telegram_id == user_id)
    )
    chats_count, total_violations, avg_rep = res_stats.first() or (0, 0, 100.0)

    # Active warns count
    res_active_warns = await session.execute(
        select(func.count(Warn.id))
        .join(User, Warn.user_id == User.id)
        .where(User.telegram_id == user_id, Warn.is_active == True, Warn.expires_at > now)  # noqa: E712
    )
    active_warns = res_active_warns.scalar() or 0

    status_badge = "🟢 Отличная репутация" if active_warns == 0 else f"🟡 Есть активные предупреждения ({active_warns})"
    if avg_rep < 50:
        status_badge = "🔴 Высокий уровень риска"

    profile_text = (
        "<b>👤 Личный профиль участника</b>\n\n"
        f"• <b>Имя:</b> {user_name}\n"
        f"• <b>Юзернейм:</b> {username_str}\n"
        f"• <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"• <b>Статус:</b> {status_badge}\n"
        f"• <b>Рейтинг доверия:</b> <code>{int(avg_rep)}/100</code>\n"
        f"• <b>Групп с вашим участием:</b> {chats_count}\n"
        f"• <b>Активных предупреждений:</b> <b>{active_warns}</b>\n\n"
        "<i>Соблюдайте правила сообществ, чтобы поддерживать высокий рейтинг доверия!</i>"
    )

    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Мои предупреждения", callback_data="user:warns")],
            [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="user:home")],
        ]
    )
    await callback.message.edit_text(text=profile_text, reply_markup=back_kb)
    await callback.answer()


@router.callback_query(F.data == "user:warns")
async def handle_user_warns_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    """List all active warnings issued to user."""
    if not callback.message:
        return
    user_id = callback.from_user.id
    now = datetime.now(timezone.utc)

    res = await session.execute(
        select(Warn, Chat)
        .join(User, Warn.user_id == User.id)
        .join(Chat, Warn.chat_id == Chat.chat_id)
        .where(User.telegram_id == user_id, Warn.is_active == True, Warn.expires_at > now)  # noqa: E712
        .order_by(Warn.created_at.desc())
        .limit(10)
    )
    warn_rows = res.all()

    if not warn_rows:
        text = (
            "<b>📋 Ваши предупреждения</b>\n\n"
            "🎉 <b>У вас нет активных предупреждений!</b>\n\n"
            "Все ваши сообщения безопасны, репутация чистая."
        )
    else:
        text = f"<b>📋 Ваши активные предупреждения ({len(warn_rows)}):</b>\n\n"
        for idx, (w, ch) in enumerate(warn_rows, 1):
            date_str = w.created_at.strftime("%d.%m.%Y %H:%M") if w.created_at else "Недавно"
            exp_str = w.expires_at.strftime("%d.%m.%Y") if w.expires_at else "7 дней"
            text += (
                f"<b>{idx}. Чат: {ch.title}</b>\n"
                f"• Причина: <code>{w.reason}</code>\n"
                f"• Выдано: <i>{date_str}</i>\n"
                f"• Истекает: <i>{exp_str}</i>\n\n"
            )

    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👤 Мой профиль", callback_data="user:profile")],
            [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="user:home")],
        ]
    )
    await callback.message.edit_text(text=text, reply_markup=back_kb)
    await callback.answer()


@router.callback_query(F.data == "user:rules")
async def handle_user_rules_callback(callback: CallbackQuery) -> None:
    """Display general safety guidelines and rules for community members."""
    if not callback.message:
        return

    text = (
        "<b>📖 Правила общения и безопасность в чатах</b>\n\n"
        "Чтобы не получать предупреждения и муты от бота:\n\n"
        "1. <b>Без спама и рекламы:</b> Не отправляйте несанкционированные ссылки на сторонние каналы и ботов.\n"
        "2. <b>Уважение к участникам:</b> Запрещены прямые оскорбления, травля и агрессивный мат в адрес людей.\n"
        "3. <b>Безопасность:</b> Строго запрещены финансовые скам-схемы, крипто-раздачи и вредоносные файлы.\n"
        "4. <b>Медиа:</b> В группах с защитой запрещен 18+ контент, шок-контент и спам стикерами.\n\n"
        "<i>Если бот выдал вам предупреждение по ошибке, вы можете нажать кнопку «Апелляция» прямо под сообщением бота!</i>"
    )
    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="user:home")],
        ]
    )
    await callback.message.edit_text(text=text, reply_markup=back_kb)
    await callback.answer()


@router.callback_query(F.data == "user:help")
async def handle_user_help_callback(callback: CallbackQuery) -> None:
    """Display list of available commands for members and admins."""
    if not callback.message:
        return

    text = (
        "<b>❓ Доступные команды бота:</b>\n\n"
        "<b>Для всех участников (в группах):</b>\n"
        "• <code>/me</code> или <code>/profile</code> — показать свой профиль и варны в этом чате\n"
        "• <code>/rules</code> — правила сообщества\n"
        "• <code>/report</code> (в ответ на сообщение) — пожаловаться админам на спам\n\n"
        "<b>Для администраторов (в группах):</b>\n"
        "• <code>/warn [причина]</code> (в ответ) — выдать предупреждение\n"
        "• <code>/unwarn</code> (в ответ) — снять предупреждение\n"
        "• <code>/clearwarns</code> (в ответ) — очистить все варны пользователя\n"
        "• <code>/mute [время, напр. 30m, 2h, 1d]</code> (в ответ) — выдать мут\n"
        "• <code>/unmute</code> (в ответ) — снять мут\n"
        "• <code>/ban [причина]</code> (в ответ) — заблокировать участника\n"
        "• <code>/admin</code> — управление доверенными администраторами\n"
        "• <code>/settings</code> — настройки модерации и фильтров"
    )
    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="user:home")],
        ]
    )
    await callback.message.edit_text(text=text, reply_markup=back_kb)
    await callback.answer()


# ==========================================
# In-Group Commands for Regular Members
# ==========================================

@router.message(Command("me", "profile", "mywarns", "warns"))
async def handle_in_chat_profile_command(message: Message, session: AsyncSession) -> None:
    """Show member status, warns, and reputation in the current chat."""
    if message.chat.id > 0 or not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Участник"
    now = datetime.now(timezone.utc)

    # Fetch Chat & User DB
    res_c = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = res_c.scalar_one_or_none()
    warn_limit = chat_db.warn_limit if chat_db else 3

    res_u = await session.execute(
        select(User).where(User.chat_id == chat_id, User.telegram_id == user_id)
    )
    user_db = res_u.scalar_one_or_none()

    if not user_db:
        active_warns = 0
        rep_score = 100
    else:
        rep_score = user_db.reputation_score
        res_w = await session.execute(
            select(func.count(Warn.id)).where(
                Warn.user_id == user_db.id,
                Warn.chat_id == chat_id,
                Warn.is_active == True,  # noqa: E712
                Warn.expires_at > now,
            )
        )
        active_warns = res_w.scalar() or 0

    status = "🟢 Нарушений нет" if active_warns == 0 else f"⚠️ Предупреждений: {active_warns}/{warn_limit}"

    text = (
        f"<b>👤 Профиль участника: {user_name}</b>\n\n"
        f"• <b>Статус:</b> {status}\n"
        f"• <b>Предупреждения:</b> <code>{active_warns} / {warn_limit}</code>\n"
        f"• <b>Рейтинг доверия:</b> <code>{rep_score}/100</code>\n"
        f"• <b>ID:</b> <code>{user_id}</code>"
    )
    await message.reply(text=text)


@router.message(Command("rules"))
async def handle_in_chat_rules_command(message: Message) -> None:
    """Show chat rules in group."""
    if message.chat.id > 0:
        return
    text = (
        "<b>📖 Правила сообщества</b>\n\n"
        "• Запрещены спам, несогласованная реклама и промо-ссылки.\n"
        "• Запрещены прямые оскорбления, травля и агрессивный мат.\n"
        "• Запрещены вредоносные ссылки, крипто-скам и 18+ контент.\n\n"
        "<i>Бот TelegramWarden круглосуточно следит за порядком в чате.</i>"
    )
    await message.reply(text=text)


@router.message(Command("report"))
async def handle_in_chat_report_command(message: Message, session: AsyncSession) -> None:
    """Allow chat members to report messages (routed to Admins or instant AI check per chat settings)."""
    if message.chat.id > 0 or not message.reply_to_message:
        await message.reply("Ответьте командой <code>/report</code> на подозрительное сообщение, чтобы отправить жалобу.")
        return

    chat_id = message.chat.id
    target_msg = message.reply_to_message
    target_user = target_msg.from_user
    if not target_user:
        return

    reporter = message.from_user
    reporter_name = reporter.first_name if reporter else "Участник"
    target_name = target_user.first_name or "Пользователь"
    target_id = target_user.id
    snippet = (target_msg.text or target_msg.caption or "[Медиафайл]")[:300]

    # Fetch Chat DB
    res_c = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = res_c.scalar_one_or_none()
    if not chat_db:
        chat_db = Chat(chat_id=chat_id, title=message.chat.title or "Chat")
        session.add(chat_db)
        await session.flush()

    report_mode = getattr(chat_db, 'report_mode', 'admin_only') or 'admin_only'

    # MODE 1: Instant AI Verification
    if report_mode == "ai_instant":
        status_msg = await message.reply("🔍 Жалоба принята. Проверяю сообщение через нейросеть...")
        raw_text = target_msg.text or target_msg.caption or ""
        sanitized = TextSanitizer.sanitize(raw_text)

        from services.ai.client import ai_dispatcher
        verdict = await ai_dispatcher.analyze_message(
            message_text=sanitized.clean_text,
            user_info=f"Reported message from {target_user.id} in {chat_id}",
        )

        if verdict.is_violation:
            # Delete reported message
            try:
                await target_msg.delete()
            except Exception:
                pass

            # Sanction the offender (target_user)
            user_db = await SanctionsExecutor.get_or_create_user(
                session=session,
                chat_id=chat_id,
                telegram_id=target_user.id,
                username=target_user.username,
                first_name=target_user.first_name,
            )

            # Apply sanction
            if verdict.suggested_action == "ban_user" or verdict.category.value in ["crypto_scam", "illegal_contraband"]:
                await SanctionsExecutor.ban_user(message.bot, session, chat_id, user_db, reason=verdict.reason)
                sanction_text = f"нарушитель <b>{target_name}</b> заблокирован"
            else:
                active_warns = await SanctionsExecutor.apply_warn(
                    message.bot, session, chat_db, user_db, reason=verdict.reason, category=verdict.category.value
                )
                sanction_text = f"нарушителю <b>{target_name}</b> выдан варн ({active_warns}/{chat_db.warn_limit})"

            await session.commit()
            await status_msg.edit_text(
                f"✅ <b>Спасибо за жалобу, {reporter_name}!</b>\n\n"
                f"ИИ подтвердил нарушение (<code>{verdict.category.value}</code>, {verdict.confidence}%).\n"
                f"Сообщение удалено, {sanction_text}."
            )
            return
        else:
            await status_msg.edit_text(
                f"<b>Жалоба от {reporter_name} проверена.</b>\n\n"
                "Признаков явного спама или нарушений не обнаружено. Информация сохранена для администраторов."
            )
            return

    # MODE 2: Admin-Only Review (Dispatch verification card to Admins/Log Channel)
    log_channel = chat_db.log_channel_id

    report_text = (
        "🚨 <b>Жалоба на сообщение от участника</b>\n\n"
        f"• <b>Чат:</b> {message.chat.title or chat_id}\n"
        f"• <b>Автор жалобы:</b> {reporter_name} (ID: <code>{reporter.id if reporter else 0}</code>)\n"
        f"• <b>Нарушитель:</b> {target_name} (ID: <code>{target_id}</code>)\n"
        f"• <b>Текст СМС:</b> <i>«{snippet}»</i>"
    )

    report_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑️ Удалить",
                    callback_data=f"rep:del:{chat_id}:{target_msg.message_id}",
                ),
                InlineKeyboardButton(
                    text="⚠️ Варн",
                    callback_data=f"rep:warn:{chat_id}:{target_id}",
                ),
                InlineKeyboardButton(
                    text="⛔ Бан",
                    callback_data=f"rep:ban:{chat_id}:{target_id}",
                ),
            ]
        ]
    )

    if log_channel:
        try:
            await message.bot.send_message(chat_id=log_channel, text=report_text, reply_markup=report_kb)
            await message.reply("✅ Жалоба успешно отправлена администраторам в журнал модерации.")
            return
        except Exception:
            pass

    await message.reply("✅ Жалоба принята. Администраторы уведомлены.", reply_markup=report_kb)

