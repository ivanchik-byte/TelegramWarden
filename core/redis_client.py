"""Async Redis client management and caching helper."""

from typing import Optional
import redis.asyncio as aioredis
from core.config import settings
from core.logger import logger


class RedisManager:
    """Singleton connection manager for asynchronous Redis operations."""

    def __init__(self) -> None:
        self._redis: Optional[aioredis.Redis] = None

    async def get_client(self) -> aioredis.Redis:
        """Get or initialize the async Redis client."""
        if self._redis is None:
            logger.info(f"Connecting to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}...")
            self._redis = aioredis.from_url(
                settings.redis_connection_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
            )
        return self._redis

    async def close(self) -> None:
        """Gracefully close Redis connections."""
        if self._redis is not None:
            logger.info("Closing Redis connection...")
            await self._redis.aclose()
            self._redis = None
            logger.info("Redis connection closed.")

    async def is_healthy(self) -> bool:
        """Check Redis connectivity."""
        try:
            client = await self.get_client()
            return await client.ping()
        except Exception as err:
            logger.warning(f"Redis health check failed: {err}")
            return False


# Global Redis manager singleton
redis_manager = RedisManager()
