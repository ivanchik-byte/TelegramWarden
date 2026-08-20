"""Asynchronous Combot Anti-Spam (CAS API) client with Redis caching (0 tokens)."""

from typing import NamedTuple, Optional
import httpx
from core.logger import logger
from core.redis_client import redis_manager

CAS_API_URL = "https://api.cas.chat/check"
REDIS_CAS_PREFIX = "warden:cas:"


class CASCheckResult(NamedTuple):
    """Result of Combot Anti-Spam check."""

    is_banned: bool
    offenses_count: int
    time_added: Optional[str]


class CASClient:
    """Checks user Telegram IDs against global CAS spammer database."""

    @classmethod
    async def check_user(cls, telegram_id: int) -> CASCheckResult:
        """Check if user is listed in CAS database with Redis caching."""
        redis_key = f"{REDIS_CAS_PREFIX}{telegram_id}"

        # 1. Check Redis Cache
        try:
            redis = await redis_manager.get_client()
            cached_val = await redis.get(redis_key)
            if cached_val is not None:
                is_banned = (cached_val == "1")
                return CASCheckResult(is_banned=is_banned, offenses_count=1 if is_banned else 0, time_added=None)
        except Exception as err:
            logger.warning(f"Redis CAS cache read error: {err}")

        # 2. Query CAS REST API
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{CAS_API_URL}?user_id={telegram_id}")
                if resp.status_code == 200:
                    data = resp.json()
                    is_banned = bool(data.get("ok", False))
                    offenses = int(data.get("result", {}).get("offenses", 0)) if is_banned else 0
                    time_added = data.get("result", {}).get("time_added")

                    # 3. Cache result in Redis
                    try:
                        redis = await redis_manager.get_client()
                        # Cache banned users for 7 days (604800s), clean users for 24h (86400s)
                        ttl = 604800 if is_banned else 86400
                        await redis.set(redis_key, "1" if is_banned else "0", ex=ttl)
                    except Exception as cache_err:
                        logger.warning(f"Redis CAS cache write error: {cache_err}")

                    return CASCheckResult(
                        is_banned=is_banned,
                        offenses_count=offenses,
                        time_added=time_added,
                    )

        except Exception as err:
            logger.warning(f"CAS API request failed for user {telegram_id}: {err}")

        # Safe fallback: if CAS is unreachable, do not block user
        return CASCheckResult(is_banned=False, offenses_count=0, time_added=None)
