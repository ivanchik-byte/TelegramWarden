"""Unit tests for CASClient global spammer database integration."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.reputation.cas import CASClient, CASCheckResult


@pytest.mark.asyncio
async def test_cas_client_banned_user():
    """Verify that CASClient correctly identifies banned user ID from API response."""
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)  # Cache miss
    mock_redis.set = AsyncMock(return_value=True)

    with patch("core.redis_client.redis_manager.get_client", return_value=mock_redis), \
         patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "ok": True,
            "result": {
                "offenses": 3,
                "time_added": 1700000000,
            },
        }
        mock_get.return_value = mock_resp

        result = await CASClient.check_user(telegram_id=987654321)

        assert isinstance(result, CASCheckResult)
        assert result.is_banned is True
        assert result.offenses_count == 3


@pytest.mark.asyncio
async def test_cas_client_clean_user():
    """Verify that CASClient returns is_banned=False for clean user."""
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)  # Cache miss
    mock_redis.set = AsyncMock(return_value=True)

    with patch("core.redis_client.redis_manager.get_client", return_value=mock_redis), \
         patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": False, "description": "Not banned"}
        mock_get.return_value = mock_resp

        result = await CASClient.check_user(telegram_id=123456789)

        assert result.is_banned is False
        assert result.offenses_count == 0
