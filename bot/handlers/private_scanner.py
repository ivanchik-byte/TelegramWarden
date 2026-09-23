"""Live AI scanner for private chats (text and media forward inspection)."""

import io
from aiogram import F, Router
from aiogram.types import Message
from services.ai.client import ai_dispatcher
from services.ai.normalizer import TextSanitizer
from services.media.pipeline import MediaModerationPipeline

router = Router(name="private_scanner")


@router.message(F.chat.type == "private", F.text & ~F.text.startswith("/"))
async def handle_private_text_scan(message: Message) -> None:
    """Scan arbitrary text or links sent to the bot in private chat."""
    raw_text = message.text or ""
    sanitized = TextSanitizer.sanitize(raw_text)

    status_msg = await message.reply("Проверяю сообщение...")

    verdict = await ai_dispatcher.analyze_message(
        message_text=sanitized.clean_text,
        user_info=f"Private scan by user {message.from_user.id}",
        cache_user_id=message.from_user.id if message.from_user else None,
    )

    if verdict.is_violation:
        result_text = (
            "<b>Результат проверки: найдено нарушение</b>\n\n"
            f"<b>Категория:</b> <code>{verdict.category.value}</code>\n"
            f"<b>Вероятность:</b> <b>{verdict.confidence}%</b>\n"
            f"<b>Рекомендуемое действие:</b> <code>{verdict.suggested_action.value}</code>\n\n"
            f"<b>Причина:</b>\n{verdict.reason}\n\n"
            "<i>В группе такое сообщение было бы автоматически удалено.</i>"
        )
    else:
        result_text = (
            "<b>Результат проверки: нарушений не обнаружено</b>\n\n"
            f"<b>Вероятность нарушения:</b> <b>{verdict.confidence}%</b>\n"
            "<b>Вердикт:</b> Признаков спама, рекламы, мошенничества или запрещенных ссылок не найдено."
        )

    await status_msg.edit_text(result_text)


@router.message(F.chat.type == "private", F.photo | F.video | F.video_note | F.sticker)
async def handle_private_media_scan(message: Message) -> None:
    """Scan arbitrary media sent to the bot in private chat via local pipeline."""
    status_msg = await message.reply("Проверяю медиафайл...")

    file_target = message.photo[-1] if message.photo else (message.video or message.sticker or message.video_note)
    if not file_target:
        await status_msg.edit_text("Не удалось прочитать медиафайл.")
        return

    try:
        buffer = io.BytesIO()
        await message.bot.download(file_target, destination=buffer)
        media_bytes = buffer.getvalue()
    except Exception as err:
        await status_msg.edit_text(f"Ошибка загрузки: {err}")
        return

    verdict = await MediaModerationPipeline.process_media(
        media_bytes=media_bytes,
        media_type="photo" if message.photo else "video",
    )

    if verdict.is_violation:
        result_text = (
            "<b>Результат проверки: найдено нарушение</b>\n\n"
            f"<b>Категория:</b> <code>{verdict.category.value}</code>\n"
            f"<b>Уверенность:</b> <b>{verdict.confidence}%</b>\n"
            f"<b>Причина:</b> {verdict.reason}\n"
            f"<b>Рекомендованное действие:</b> <code>{verdict.suggested_action.value}</code>"
        )
    else:
        result_text = (
            "<b>Результат проверки: нарушений не обнаружено</b>\n\n"
            "<b>Вердикт:</b> Запрещенного контента (NSFW) и рекламных QR-кодов не обнаружено."
        )

    await status_msg.edit_text(result_text)
