"""Anti-Raid and flood-join panic mode detector using Redis sliding window."""

import time
from typing import NamedTuple
from core.logger import logger
from core.redis_client import redis_manager

REDIS_RAID_JOIN_PREFIX = "warden:raid:joins:"
REDIS_RAID_LOCKDOWN_PREFIX = "warden:raid:lockdown:"


class AntiRaidStatus(NamedTuple):
    """Status container for group raid state."""

    is_under_raid: bool
    join_count_in_window: int
    lockdown_active: bool


class AntiRaidDetector:
    """Detects sudden mass-join raids using a Redis timestamp sliding window."""

    @classmethod
    async def record_join_and_check(
        cls,
        chat_id: int,
        window_seconds: int = 15,
        threshold_joins: int = 8,
        lockdown_duration_seconds: int = 300,
    ) -> AntiRaidStatus:
        """Record new join event and check if threshold is breached."""
        try:
            redis = await redis_manager.get_client()
            lockdown_key = f"{REDIS_RAID_LOCKDOWN_PREFIX}{chat_id}"
            joins_key = f"{REDIS_RAID_JOIN_PREFIX}{chat_id}"

            # Check if chat is already under active lockdown
            lockdown_val = await redis.get(lockdown_key)
            if lockdown_val is not None:
                return AntiRaidStatus(is_under_raid=True, join_count_in_window=999, lockdown_active=True)

            now = time.time()
            cutoff = now - window_seconds

            # Add current join timestamp to sorted set
            pipe = redis.pipeline()
            pipe.zremrangebyscore(joins_key, "-inf", cutoff)
            pipe.zadd(joins_key, {str(now): now})
            pipe.zcard(joins_key)
            pipe.expire(joins_key, window_seconds + 5)
            results = await pipe.execute()

            join_count = results[2]

            # Check if threshold is breached
            if join_count >= threshold_joins:
                logger.warning(
                    f"Raid detected in chat {chat_id}! {join_count} joins in {window_seconds}s. Activating lockdown."
                )
                await redis.set(lockdown_key, "1", ex=lockdown_duration_seconds)
                return AntiRaidStatus(is_under_raid=True, join_count_in_window=join_count, lockdown_active=True)

            return AntiRaidStatus(is_under_raid=False, join_count_in_window=join_count, lockdown_active=False)

        except Exception as err:
            logger.error(f"AntiRaid check error for chat {chat_id}: {err}")
            return AntiRaidStatus(is_under_raid=False, join_count_in_window=0, lockdown_active=False)
