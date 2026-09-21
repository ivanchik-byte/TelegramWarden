"""Perceptual hashing and spam deduplication using Redis."""

import asyncio
import io
from typing import Optional
from PIL import Image
import imagehash
from core.redis_client import redis_manager
from core.logger import logger

REDIS_PHASH_KEY = "warden:spam_hashes"


def _closest_match(target: str, candidates: list[str], max_distance: int) -> bool:
    try:
        needle = imagehash.hex_to_hash(target)
    except ValueError:
        return False
    for raw in candidates:
        try:
            distance = needle - imagehash.hex_to_hash(raw)
        except ValueError:
            continue
        if distance <= max_distance:
            logger.info(f"pHash match found (distance: {distance}) against known spam {raw}")
            return True
    return False


class PHashDeduplicator:
    """Calculates perceptual hashes and checks against known spam database in Redis."""

    @classmethod
    def compute_hash(cls, image_bytes: bytes) -> Optional[str]:
        """Compute 64-bit perceptual hash string from raw image bytes."""
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                hash_obj = imagehash.phash(img)
                return str(hash_obj)
        except Exception as err:
            logger.warning(f"Failed to compute image pHash: {err}")
            return None

    @classmethod
    async def is_known_spam(cls, phash_str: str, max_distance: int = 4) -> bool:
        """Check if image hash matches any known spam hash within Hamming distance."""
        if not phash_str:
            return False

        try:
            redis = await redis_manager.get_client()
            raw_hashes = await redis.smembers(REDIS_PHASH_KEY)
            if not raw_hashes:
                return False
            candidates = [h.decode() if isinstance(h, bytes) else h for h in raw_hashes]
            return await asyncio.to_thread(_closest_match, phash_str, candidates, max_distance)
        except Exception as err:
            logger.error(f"Error checking spam pHash in Redis: {err}")
            return False

    @classmethod
    async def register_spam_hash(cls, phash_str: str) -> None:
        """Register a confirmed spam image hash into Redis database."""
        if not phash_str:
            return

        try:
            redis = await redis_manager.get_client()
            await redis.sadd(REDIS_PHASH_KEY, phash_str)
            logger.info(f"Registered new spam pHash: {phash_str}")
        except Exception as err:
            logger.error(f"Failed to save spam pHash to Redis: {err}")
