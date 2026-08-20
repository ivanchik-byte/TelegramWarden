"""Captcha verification session management and restrictions."""

from typing import Optional
from core.logger import logger
from core.redis_client import redis_manager

REDIS_CAPTCHA_PREFIX = "warden:captcha:"


class CaptchaManager:
    """Manages active newcomer captcha challenges in Redis."""

    @classmethod
    async def create_challenge(
        cls,
        chat_id: int,
        user_id: int,
        message_id: int,
        timeout_seconds: int = 120,
    ) -> bool:
        """Record an active captcha challenge in Redis."""
        try:
            redis = await redis_manager.get_client()
            key = f"{REDIS_CAPTCHA_PREFIX}{chat_id}:{user_id}"
            await redis.set(key, str(message_id), ex=timeout_seconds)
            return True
        except Exception as err:
            logger.error(f"Failed to create captcha session: {err}")
            return False

    @classmethod
    async def get_challenge_message_id(cls, chat_id: int, user_id: int) -> Optional[int]:
        """Get the message ID of the pending captcha challenge."""
        try:
            redis = await redis_manager.get_client()
            key = f"{REDIS_CAPTCHA_PREFIX}{chat_id}:{user_id}"
            val = await redis.get(key)
            return int(val) if val else None
        except Exception as err:
            logger.error(f"Failed to get captcha message ID: {err}")
            return None

    @classmethod
    async def complete_challenge(cls, chat_id: int, user_id: int) -> bool:
        """Mark captcha as completed and remove session."""
        try:
            redis = await redis_manager.get_client()
            key = f"{REDIS_CAPTCHA_PREFIX}{chat_id}:{user_id}"
            deleted = await redis.delete(key)
            return deleted > 0
        except Exception as err:
            logger.error(f"Failed to complete captcha session: {err}")
            return False
