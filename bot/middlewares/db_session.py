"""Database session middleware injecting SQLAlchemy AsyncSession into handlers."""

from collections.abc import Awaitable, Callable
from typing import Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from core.database import async_session_factory
from core.logger import logger


class DBSessionMiddleware(BaseMiddleware):
    """Middleware that injects an isolated async SQLAlchemy session into every update context."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with async_session_factory() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception as err:
                await session.rollback()
                logger.error(f"Middleware session error: {err}")
                raise
            finally:
                await session.close()
