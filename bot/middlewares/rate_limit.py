"""Anti-flood and rate-limiting middleware using Redis sliding window."""

import time
from collections.abc import Awaitable, Callable
from typing import Any
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from core.logger import logger
from core.redis_client import redis_manager

REDIS_RATELIMIT_PREFIX = "warden:ratelimit:"


class RateLimitMiddleware(BaseMiddleware):
    """Protects groups from flood by enforcing message rate limits per user."""

    def __init__(self, max_messages: int = 5, window_seconds: int = 4) -> None:
        self.max_messages = max_messages
        self.window_seconds = window_seconds

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.from_user or not event.chat:
            return await handler(event, data)

        chat_id = event.chat.id
        user_id = event.from_user.id

        # Skip rate limit for private messages or channel system events
        if chat_id > 0 or event.from_user.is_bot:
            return await handler(event, data)

        try:
            redis = await redis_manager.get_client()
            key = f"{REDIS_RATELIMIT_PREFIX}{chat_id}:{user_id}"
            now = time.time()
            cutoff = now - self.window_seconds

            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, "-inf", cutoff)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, self.window_seconds + 2)
            results = await pipe.execute()

            msg_count = results[2]
            if msg_count > self.max_messages:
                logger.warning(f"User {user_id} triggered flood in chat {chat_id} ({msg_count} msgs/{self.window_seconds}s)")
                try:
                    await event.delete()
                except Exception:
                    pass
                return None

        except Exception as err:
            logger.debug(f"RateLimit middleware error: {err}")

        return await handler(event, data)
