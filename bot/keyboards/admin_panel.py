"""Comprehensive inline keyboards for the private Admin Control Panel."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from models import Chat


def get_admin_main_menu_keyboard(
    chats: list[Chat],
    bot_username: str,
    webapp_url: str = "",
) -> InlineKeyboardMarkup:
    """Generate main admin dashboard with managed groups list."""
    buttons = []

    # 1. Mini App WebApp Button (if URL configured)
    if webapp_url and webapp_url.startswith("https://") and "localhost" not in webapp_url:
        buttons.append([
            InlineKeyboardButton(
                text="Открыть Mini App Дашборд",
                web_app=WebAppInfo(url=webapp_url),
            )
        ])

    # 2. List of managed groups
    if chats:
        for chat in chats[:8]:
            title = chat.title or f"Chat {chat.chat_id}"
            buttons.append([
                InlineKeyboardButton(
                    text=f"Группа: {title}",
                    callback_data=f"adm:chat:{chat.chat_id}",
                )
            ])

    # 3. Add to new group button
    buttons.append([
        InlineKeyboardButton(
            text="Добавить бота в новую группу",
            url=f"https://t.me/{bot_username}?startgroup=true",
        )
    ])

    # 4. Scanner & Help
    buttons.append([
        InlineKeyboardButton(
            text="ИИ-Сканер в ЛС",
            callback_data="adm:scanner_info",
        ),
        InlineKeyboardButton(
            text="Справка",
            callback_data="adm:help",
        ),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_chat_details_keyboard(chat_db: Chat, webapp_url: str = "") -> InlineKeyboardMarkup:
    """Generate management card for a specific group."""
    chat_id = chat_db.chat_id
    status_text = "ВКЛЮЧЕНА" if chat_db.is_active else "ВЫКЛЮЧЕНА"

    buttons = []

    # Mini App Button
    if webapp_url and webapp_url.startswith("https://") and "localhost" not in webapp_url:
        group_app_url = f"{webapp_url}?chat_id={chat_id}" if "?" not in webapp_url else f"{webapp_url}&chat_id={chat_id}"
        buttons.append([
            InlineKeyboardButton(
                text="Открыть Mini App Дашборд",
                web_app=WebAppInfo(url=group_app_url),
            )
        ])

    buttons.extend([
        [
            InlineKeyboardButton(
                text=f"Главная защита: [{status_text}]",
                callback_data=f"adm:tgl:active:{chat_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="Настройки фильтров",
                callback_data=f"adm:filters:{chat_id}",
            ),
            InlineKeyboardButton(
                text="Вайтлист и Админы",
                callback_data=f"adm:whitelist:{chat_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="Ночной режим (Часы)",
                callback_data=f"adm:night_cfg:{chat_id}",
            ),
            InlineKeyboardButton(
                text="Статистика",
                callback_data=f"adm:stats:{chat_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="Журнал логов",
                callback_data=f"adm:logs:{chat_id}",
            ),
            InlineKeyboardButton(
                text="Назад ко всем группам",
                callback_data="adm:menu",
            ),
        ],
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_chat_filters_keyboard(chat_db: Chat) -> InlineKeyboardMarkup:
    """Generate fine-grained filter toggles for group."""
    chat_id = chat_db.chat_id

    captcha_st = "ВКЛ" if chat_db.captcha_enabled else "ВЫКЛ"
    raid_st = "ВКЛ" if chat_db.anti_raid_enabled else "ВЫКЛ"
    chan_st = "ЗАПРЕЩЕНЫ" if not chat_db.allow_sender_chat else "РАЗРЕШЕНЫ"
    serv_st = "УДАЛЯТЬ" if chat_db.clean_service_messages else "ОСТАВЛЯТЬ"
    ai_st = "ВКЛ" if chat_db.ai_moderation_enabled else "ВЫКЛ"
    punish_st = "БАН" if chat_db.warn_punishment == "ban" else "МУТ 24Ч"

    night_st = f"ВКЛ ({chat_db.night_mode_start}-{chat_db.night_mode_end})" if chat_db.night_mode_enabled else "ВЫКЛ"
    thresh = int(chat_db.ai_confidence_threshold)

    buttons = [
        [
            InlineKeyboardButton(
                text=f"Капча новичков: [{captcha_st}]",
                callback_data=f"adm:tgl:captcha:{chat_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"Анти-Рейд Паник-Мод: [{raid_st}]",
                callback_data=f"adm:tgl:raid:{chat_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"Отправка от каналов: [{chan_st}]",
                callback_data=f"adm:tgl:channels:{chat_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"Очистка системных смс: [{serv_st}]",
                callback_data=f"adm:tgl:service:{chat_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"ИИ-анализ спама: [{ai_st}]",
                callback_data=f"adm:tgl:ai:{chat_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"Режим наказания за варны: [{punish_st}]",
                callback_data=f"adm:tgl:punish:{chat_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"Ночной режим: [{night_st}]",
                callback_data=f"adm:tgl:night:{chat_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="Настроить часы ночи",
                callback_data=f"adm:night_cfg:{chat_id}",
            )
        ],
        # AI Sensitivity Adjuster
        [
            InlineKeyboardButton(
                text="Порог ИИ: -5%",
                callback_data=f"adm:sens:minus:{chat_id}",
            ),
            InlineKeyboardButton(
                text=f"{thresh}%",
                callback_data="adm:noop",
            ),
            InlineKeyboardButton(
                text="Порог ИИ: +5%",
                callback_data=f"adm:sens:plus:{chat_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="Назад к группе",
                callback_data=f"adm:chat:{chat_id}",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_night_mode_config_keyboard(chat_db: Chat) -> InlineKeyboardMarkup:
    """Generate fine-grained night mode schedule adjustments."""
    chat_id = chat_db.chat_id
    status_st = "ВКЛЮЧЕН" if chat_db.night_mode_enabled else "ВЫКЛЮЧЕН"

    buttons = [
        [
            InlineKeyboardButton(
                text=f"Статус ночного режима: [{status_st}]",
                callback_data=f"adm:tgl:night:{chat_id}",
            )
        ],
        # Start hour adjustment
        [
            InlineKeyboardButton(
                text="Начало -1ч",
                callback_data=f"adm:nhour:s_minus:{chat_id}",
            ),
            InlineKeyboardButton(
                text=f"Старт: {chat_db.night_mode_start}",
                callback_data="adm:noop",
            ),
            InlineKeyboardButton(
                text="Начало +1ч",
                callback_data=f"adm:nhour:s_plus:{chat_id}",
            ),
        ],
        # End hour adjustment
        [
            InlineKeyboardButton(
                text="Конец -1ч",
                callback_data=f"adm:nhour:e_minus:{chat_id}",
            ),
            InlineKeyboardButton(
                text=f"Конец: {chat_db.night_mode_end}",
                callback_data="adm:noop",
            ),
            InlineKeyboardButton(
                text="Конец +1ч",
                callback_data=f"adm:nhour:e_plus:{chat_id}",
            ),
        ],
        [
            InlineKeyboardButton(
                text="Назад к фильтрам",
                callback_data=f"adm:filters:{chat_id}",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_chat_whitelist_keyboard(chat_db: Chat) -> InlineKeyboardMarkup:
    """Generate whitelist management buttons."""
    chat_id = chat_db.chat_id
    buttons = [
        [
            InlineKeyboardButton(
                text="Добавить в вайтлист по ID",
                callback_data=f"adm:wl_add:{chat_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="Очистить вайтлист",
                callback_data=f"adm:wl_clear:{chat_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="Назад к группе",
                callback_data=f"adm:chat:{chat_id}",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_non_admin_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """Generate access restricted view for regular non-admin users."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Добавить бота в свою группу",
                    url=f"https://t.me/{bot_username}?startgroup=true",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Проверить доступ заново",
                    callback_data="adm:menu",
                )
            ],
        ]
    )
