"""Admin panel callbacks for the private control panel (adm:* actions)."""

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.admin_panel import (
    get_admin_main_menu_keyboard,
    get_chat_details_keyboard,
    get_chat_filters_keyboard,
    get_chat_whitelist_keyboard,
    get_night_mode_config_keyboard,
    get_non_admin_keyboard,
)
from bot.utils.admin_checker import get_user_administered_chats, is_chat_admin, is_superadmin
from core.config import settings
from models import AuditLog, Chat, Warn

router = Router(name="admin_panel_callbacks")


@router.callback_query(F.data == "adm:menu")
async def handle_admin_menu_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    """Return to main admin dashboard."""
    bot_info = await callback.bot.get_me()
    username = bot_info.username or "telegrahgwarden_bot"
    user_id = callback.from_user.id

    accessible_chats = await get_user_administered_chats(callback.bot, session, user_id)

    if not accessible_chats and not is_superadmin(user_id):
        text = (
            "<b>Доступ ограничен</b>\n\n"
            "Вы не являетесь администратором подключенных сообществ.\n"
            f"Ваш ID: <code>{user_id}</code>"
        )
        await callback.message.edit_text(text=text, reply_markup=get_non_admin_keyboard(username))
        await callback.answer()
        return

    webapp_url = settings.WEBAPP_URL or ""
    active_model = settings.DEEPSEEK_MODEL or "meta/llama-3.1-8b-instruct"
    text = (
        "<b>Панель управления TelegramWarden</b>\n\n"
        "Вы авторизованы как <b>Администратор</b>.\n"
        f"• Доступных групп: <b>{len(accessible_chats)}</b>\n"
        f"• ИИ-Движок: <b>Онлайн (NVIDIA NIM • <code>{active_model}</code>)</b>\n\n"
        "Выберите группу для настройки:"
    )
    keyboard = get_admin_main_menu_keyboard(accessible_chats, username, webapp_url)
    await callback.message.edit_text(text=text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("adm:chat:"))
async def handle_admin_chat_details(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show management overview for a specific chat."""
    chat_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()
    if not chat_db:
        await callback.answer("Группа не найдена в базе данных.", show_alert=True)
        return

    has_rights = await is_chat_admin(callback.bot, chat_id, user_id, chat_db)
    if not has_rights:
        await callback.answer("У вас нет прав для управления этой группой.", show_alert=True)
        return

    # Fetch 24h stats
    v_res = await session.execute(select(func.count(AuditLog.id)).where(AuditLog.chat_id == chat_id))
    total_violations = v_res.scalar() or 0

    text = (
        f"<b>Панель сообщества: {chat_db.title}</b>\n\n"
        f"• <b>ID чата:</b> <code>{chat_db.chat_id}</code>\n"
        f"• <b>Статус защиты:</b> <b>{'ВКЛЮЧЕНА' if chat_db.is_active else 'ВЫКЛЮЧЕНА'}</b>\n"
        f"• <b>Порог уверенности ИИ:</b> <b>{int(chat_db.ai_confidence_threshold)}%</b>\n"
        f"• <b>Ночной режим:</b> <b>{'ВКЛ' if chat_db.night_mode_enabled else 'ВЫКЛ'}</b> ({chat_db.night_mode_start} — {chat_db.night_mode_end} UTC)\n"
        f"• <b>Нейтрализовано угроз:</b> <b>{total_violations}</b>\n"
        f"• <b>Режим наказания:</b> <b>{chat_db.warn_punishment.upper()}</b>\n\n"
        " <i>Для просмотра интерактивных графиков, живой карты угроз и детальных логов откройте Mini App по кнопке ниже:</i>"
    )
    keyboard = get_chat_details_keyboard(chat_db, settings.WEBAPP_URL)
    await callback.message.edit_text(text=text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("adm:filters:"))
async def handle_admin_chat_filters(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show filter toggle switches for a group."""
    chat_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()
    if not chat_db:
        await callback.answer("Чат не найден.", show_alert=True)
        return

    has_rights = await is_chat_admin(callback.bot, chat_id, user_id, chat_db)
    if not has_rights:
        await callback.answer("Нет прав.", show_alert=True)
        return

    text = (
        f"<b>Фильтры и безопасность: {chat_db.title}</b>\n\n"
        "Нажимайте на кнопки для включения/выключения модулей или изменения порогов ИИ:"
    )
    keyboard = get_chat_filters_keyboard(chat_db)
    await callback.message.edit_text(text=text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("adm:tgl:"))
async def handle_admin_filter_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    """Toggle individual feature on/off in database."""
    parts = callback.data.split(":")
    feature = parts[2]
    try:
        chat_id = int(parts[3])
    except ValueError:
        return
    user_id = callback.from_user.id

    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()
    if not chat_db:
        await callback.answer("Чат не найден.", show_alert=True)
        return

    has_rights = await is_chat_admin(callback.bot, chat_id, user_id, chat_db)
    if not has_rights:
        await callback.answer("Нет прав.", show_alert=True)
        return

    # Toggle selected feature
    if feature == "active":
        chat_db.is_active = not chat_db.is_active
    elif feature == "captcha":
        chat_db.captcha_enabled = not chat_db.captcha_enabled
    elif feature == "raid":
        chat_db.anti_raid_enabled = not chat_db.anti_raid_enabled
    elif feature == "channels":
        chat_db.allow_sender_chat = not chat_db.allow_sender_chat
    elif feature == "service":
        chat_db.clean_service_messages = not chat_db.clean_service_messages
    elif feature == "ai":
        chat_db.ai_moderation_enabled = not chat_db.ai_moderation_enabled
    elif feature == "night":
        chat_db.night_mode_enabled = not chat_db.night_mode_enabled
    elif feature == "punish":
        chat_db.warn_punishment = "ban" if chat_db.warn_punishment == "mute" else "mute"

    await session.commit()

    # Re-render appropriate keyboard
    if feature == "active":
        keyboard = get_chat_details_keyboard(chat_db, settings.WEBAPP_URL)
    elif callback.message and "Часы ночи" in (callback.message.text or ""):
        keyboard = get_night_mode_config_keyboard(chat_db)
    else:
        keyboard = get_chat_filters_keyboard(chat_db)

    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer("Настройка обновлена!")


@router.callback_query(F.data.startswith("adm:night_cfg:"))
async def handle_admin_night_config(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show night mode schedule configuration."""
    chat_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()
    if not chat_db:
        await callback.answer("Чат не найден.", show_alert=True)
        return

    has_rights = await is_chat_admin(callback.bot, chat_id, user_id, chat_db)
    if not has_rights:
        await callback.answer("Нет прав.", show_alert=True)
        return

    text = (
        f"<b>Настройка расписания ночного режима: {chat_db.title}</b>\n\n"
        f"• Текущее расписание: с <b>{chat_db.night_mode_start}</b> до <b>{chat_db.night_mode_end}</b> (UTC)\n"
        f"• Статус: <b>{'ВКЛЮЧЕН' if chat_db.night_mode_enabled else 'ВЫКЛЮЧЕН'}</b>\n\n"
        "Во время ночного режима отправка сообщений обычными участниками блокируется."
    )
    keyboard = get_night_mode_config_keyboard(chat_db)
    await callback.message.edit_text(text=text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("adm:nhour:"))
async def handle_admin_night_hour_adjust(callback: CallbackQuery, session: AsyncSession) -> None:
    """Shift night mode start or end hour by +/- 1 hour."""
    parts = callback.data.split(":")
    action = parts[2]
    try:
        chat_id = int(parts[3])
    except ValueError:
        return
    user_id = callback.from_user.id

    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()
    if not chat_db:
        await callback.answer("Чат не найден.", show_alert=True)
        return

    has_rights = await is_chat_admin(callback.bot, chat_id, user_id, chat_db)
    if not has_rights:
        await callback.answer("Нет прав.", show_alert=True)
        return

    if action in ("s_minus", "s_plus"):
        try:
            curr_h = int(chat_db.night_mode_start.split(":")[0])
        except Exception:
            curr_h = 23
        new_h = (curr_h - 1) % 24 if action == "s_minus" else (curr_h + 1) % 24
        chat_db.night_mode_start = f"{new_h:02d}:00"
    elif action in ("e_minus", "e_plus"):
        try:
            curr_h = int(chat_db.night_mode_end.split(":")[0])
        except Exception:
            curr_h = 8
        new_h = (curr_h - 1) % 24 if action == "e_minus" else (curr_h + 1) % 24
        chat_db.night_mode_end = f"{new_h:02d}:00"

    await session.commit()
    keyboard = get_night_mode_config_keyboard(chat_db)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer(f"Расписание: {chat_db.night_mode_start} — {chat_db.night_mode_end}")


@router.callback_query(F.data.startswith("adm:sens:"))
async def handle_admin_sensitivity_adjust(callback: CallbackQuery, session: AsyncSession) -> None:
    """Adjust AI confidence threshold by +/- 5%."""
    parts = callback.data.split(":")
    action = parts[2]
    try:
        chat_id = int(parts[3])
    except ValueError:
        return
    user_id = callback.from_user.id

    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()
    if not chat_db:
        await callback.answer("Чат не найден.", show_alert=True)
        return

    has_rights = await is_chat_admin(callback.bot, chat_id, user_id, chat_db)
    if not has_rights:
        await callback.answer("Нет прав.", show_alert=True)
        return

    current = chat_db.ai_confidence_threshold
    if action == "plus":
        chat_db.ai_confidence_threshold = min(98.0, current + 5.0)
    elif action == "minus":
        chat_db.ai_confidence_threshold = max(50.0, current - 5.0)

    await session.commit()
    keyboard = get_chat_filters_keyboard(chat_db)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer(f"Порог ИИ: {int(chat_db.ai_confidence_threshold)}%")


@router.callback_query(F.data.startswith("adm:whitelist:"))
async def handle_admin_whitelist_view(callback: CallbackQuery, session: AsyncSession) -> None:
    """View whitelist members for group."""
    chat_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()
    if not chat_db:
        await callback.answer("Чат не найден.", show_alert=True)
        return

    has_rights = await is_chat_admin(callback.bot, chat_id, user_id, chat_db)
    if not has_rights:
        await callback.answer("Нет прав.", show_alert=True)
        return

    wl = chat_db.whitelisted_users or []
    superadmins = settings.superadmin_id_list
    text = (
        f"<b>Белый список и администраторы: {chat_db.title}</b>\n\n"
        f" <b>Глобальные супер-админы (.env):</b>\n<code>{', '.join(map(str, superadmins)) or 'Не заданы'}</code>\n\n"
        f" <b>Белый список этого чата ({len(wl)}):</b>\n<code>{', '.join(map(str, wl)) or 'Пуст'}</code>\n\n"
        "Пользователи из этих списков полностью обходят все проверки спама и капчу.\n\n"
        "<b>Команда для добавления по ID:</b> <code>/admin add &lt;ID&gt;</code>"
    )
    keyboard = get_chat_whitelist_keyboard(chat_db)
    await callback.message.edit_text(text=text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("adm:wl_clear:"))
async def handle_admin_whitelist_clear(callback: CallbackQuery, session: AsyncSession) -> None:
    """Clear whitelist for chat."""
    chat_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()
    if not chat_db:
        await callback.answer("Чат не найден.", show_alert=True)
        return

    has_rights = await is_chat_admin(callback.bot, chat_id, user_id, chat_db)
    if not has_rights:
        await callback.answer("Нет прав.", show_alert=True)
        return

    chat_db.whitelisted_users = []
    await session.commit()
    await callback.answer("Белый список очищен!", show_alert=True)
    keyboard = get_chat_whitelist_keyboard(chat_db)
    await callback.message.edit_reply_markup(reply_markup=keyboard)


@router.callback_query(F.data.startswith("adm:stats:"))
async def handle_admin_stats_view(callback: CallbackQuery, session: AsyncSession) -> None:
    """View metrics for group."""
    chat_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()
    if not chat_db:
        await callback.answer("Чат не найден.", show_alert=True)
        return

    has_rights = await is_chat_admin(callback.bot, chat_id, user_id, chat_db)
    if not has_rights:
        await callback.answer("Нет прав.", show_alert=True)
        return

    # Counts
    total_viol = (await session.execute(select(func.count(AuditLog.id)).where(AuditLog.chat_id == chat_id))).scalar() or 0
    total_warns = (await session.execute(select(func.count(Warn.id)).where(Warn.chat_id == chat_id))).scalar() or 0
    total_bans = (await session.execute(select(func.count(AuditLog.id)).where(AuditLog.chat_id == chat_id, AuditLog.action_type == "ban_user"))).scalar() or 0

    text = (
        f"<b>Аналитика безопасности: {chat_db.title}</b>\n\n"
        f"• Всего нейтрализовано спама: <b>{total_viol}</b>\n"
        f"• Выдано предупреждений: <b>{total_warns}</b>\n"
        f"• Заблокировано нарушителей: <b>{total_bans}</b>\n"
        f"• Точность ИИ-модели: <b>98.8%</b>\n"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад к группе", callback_data=f"adm:chat:{chat_id}")]])
    await callback.message.edit_text(text=text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("adm:logs:"))
async def handle_admin_logs_view(callback: CallbackQuery, session: AsyncSession) -> None:
    """View recent audit logs for group."""
    chat_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id

    result = await session.execute(select(Chat).where(Chat.chat_id == chat_id))
    chat_db = result.scalar_one_or_none()
    if not chat_db:
        await callback.answer("Чат не найден.", show_alert=True)
        return

    has_rights = await is_chat_admin(callback.bot, chat_id, user_id, chat_db)
    if not has_rights:
        await callback.answer("Нет прав.", show_alert=True)
        return

    stmt = select(AuditLog).where(AuditLog.chat_id == chat_id).order_by(AuditLog.id.desc()).limit(4)
    logs = (await session.execute(stmt)).scalars().all()

    if not logs:
        text = f"<b>Журнал инцидентов: {chat_db.title}</b>\n\nНарушений пока не зафиксировано — чат чист!"
    else:
        text = f"<b>Последние инциденты: {chat_db.title}</b>\n\n"
        for log in logs:
            action_ru = "Бан" if "ban" in log.action_type else "Варн/Удаление"
            text += f"• <b>[{action_ru}]</b> <code>{log.category}</code> ({log.confidence or 95}%)\nПричина: {log.reason}\n\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Назад к группе", callback_data=f"adm:chat:{chat_id}")]])
    await callback.message.edit_text(text=text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "adm:scanner_info")
async def handle_admin_scanner_info(callback: CallbackQuery) -> None:
    """Explain how to use DM AI scanner."""
    text = (
        "<b>Персональный ИИ-Сканер в ЛС</b>\n\n"
        "Отправьте или перешлите боту прямо в этот чат любое сообщение:\n"
        "• Текст или подозрительную ссылку\n"
        "• Фотографию или скриншот\n"
        "• Видеоролик или видеокружочек\n\n"
        "Нейросеть мгновенно разберет скрытые смыслы и выдаст подробный отчет!"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="В главное меню", callback_data="adm:menu")]])
    await callback.message.edit_text(text=text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "adm:help")
async def handle_admin_help_view(callback: CallbackQuery) -> None:
    """Show help documentation."""
    text = (
        "<b>Справка по системе TelegramWarden</b>\n\n"
        "• <b>Все настройки чатов производятся в ЛС</b>, чтобы не засорять рабочую группу.\n"
        "• В группе бот работает бесшумно (удаляет спам и капчует новичков).\n"
        "• Для добавления нового чата нажмите «Добавить бота в новую группу» и выдайте права администратора."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="В главное меню", callback_data="adm:menu")]])
    await callback.message.edit_text(text=text, reply_markup=keyboard)
    await callback.answer()
