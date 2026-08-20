"""TelegramWarden unified entry point: Aiogram 3 Bot + FastAPI Mini App API."""

import asyncio
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from api.main import app as fastapi_app
from aiogram.types import MenuButtonWebApp, WebAppInfo
from bot.handlers.admin_actions import router as admin_actions_router
from bot.handlers.admin_management import router as admin_mgmt_router
from bot.handlers.appeals import router as appeals_router
from bot.handlers.edited_messages import router as edited_router
from bot.handlers.joins import router as joins_router
from bot.handlers.media_messages import router as media_router
from bot.handlers.service_cleanup import router as cleanup_router
from bot.handlers.settings import router as settings_router
from bot.handlers.start import router as start_router
from bot.handlers.text_messages import router as text_router
from bot.middlewares.db_session import DBSessionMiddleware
from bot.middlewares.rate_limit import RateLimitMiddleware
from core.config import settings
from core.database import init_db, close_db
from core.logger import logger
from core.redis_client import redis_manager


async def run_fastapi_server() -> None:
    """Run uvicorn server for Telegram Mini App API and WebApp frontend."""
    config = uvicorn.Config(
        app=fastapi_app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    logger.info(f"FastAPI Mini App Server running on http://{settings.API_HOST}:{settings.API_PORT}")
    await server.serve()


async def main() -> None:
    """Initialize bot instance, register middlewares, attach routers and start bot + API."""
    logger.info("Starting TelegramWarden Unified Service (Bot + Mini App API)...")

    # 1. Initialize Database & Redis
    await init_db()
    await redis_manager.get_client()

    # 2. Create Bot and Dispatcher
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # 3. Register Global Middlewares
    dp.update.middleware(DBSessionMiddleware())
    dp.message.middleware(RateLimitMiddleware())

    # 4. Attach Event Routers
    dp.include_router(start_router)
    dp.include_router(admin_mgmt_router)
    dp.include_router(appeals_router)
    dp.include_router(settings_router)
    dp.include_router(admin_actions_router)
    dp.include_router(cleanup_router)
    dp.include_router(joins_router)
    dp.include_router(edited_router)
    dp.include_router(text_router)
    dp.include_router(media_router)

    logger.info("Routers and Middlewares attached successfully.")

    # Configure Telegram Menu Button for Mini App
    if settings.WEBAPP_URL and settings.WEBAPP_URL.startswith("https://"):
        try:
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="Панель управления",
                    web_app=WebAppInfo(url=settings.WEBAPP_URL),
                )
            )
            logger.info(f"Telegram Menu Button configured with WebApp: {settings.WEBAPP_URL}")
        except Exception as mb_err:
            logger.warning(f"Failed to set menu button: {mb_err}")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        # Run Bot Polling and FastAPI Server concurrently
        await asyncio.gather(
            dp.start_polling(bot),
            run_fastapi_server(),
        )
    finally:
        logger.info("Shutting down TelegramWarden...")
        await bot.session.close()
        await redis_manager.close()
        await close_db()
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
