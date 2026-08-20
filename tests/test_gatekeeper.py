"""Unit tests for CaptchaManager, AntiRaidDetector, and captcha keyboards."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from bot.keyboards.captcha import get_captcha_keyboard
from services.gatekeeper.anti_raid import AntiRaidDetector
from services.gatekeeper.captcha_manager import CaptchaManager


def test_captcha_keyboard_structure():
    """Verify inline keyboard callback data format."""
    kb = get_captcha_keyboard(user_id=12345)
    assert len(kb.inline_keyboard) == 1
    button = kb.inline_keyboard[0][0]
    assert button.text == "Я человек"
    assert button.callback_data == "captcha:verify:12345"


@pytest.mark.asyncio
async def test_captcha_manager_redis_lifecycle():
    """Verify challenge session creation, retrieval, and completion."""
    mock_redis = MagicMock()
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value="999888")
    mock_redis.delete = AsyncMock(return_value=1)

    with patch("core.redis_client.redis_manager.get_client", return_value=mock_redis):
        # 1. Create challenge
        created = await CaptchaManager.create_challenge(
            chat_id=-100123,
            user_id=555,
            message_id=999888,
            timeout_seconds=60,
        )
        assert created is True

        # 2. Get message ID
        msg_id = await CaptchaManager.get_challenge_message_id(chat_id=-100123, user_id=555)
        assert msg_id == 999888

        # 3. Complete challenge
        completed = await CaptchaManager.complete_challenge(chat_id=-100123, user_id=555)
        assert completed is True


@pytest.mark.asyncio
async def test_anti_raid_detector_lockdown_activation():
    """Verify that excessive joins in time window activate lockdown."""
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)  # not currently in lockdown
    mock_redis.set = AsyncMock(return_value=True)

    # Mock pipeline returning 12 joins (breaching threshold of 8)
    mock_pipe = MagicMock()
    mock_pipe.zremrangebyscore = MagicMock()
    mock_pipe.zadd = MagicMock()
    mock_pipe.zcard = MagicMock()
    mock_pipe.expire = MagicMock()
    mock_pipe.execute = AsyncMock(return_value=[0, 1, 12, True])
    mock_redis.pipeline.return_value = mock_pipe

    with patch("core.redis_client.redis_manager.get_client", return_value=mock_redis):
        status = await AntiRaidDetector.record_join_and_check(
            chat_id=-100555,
            window_seconds=15,
            threshold_joins=8,
            lockdown_duration_seconds=300,
        )

        assert status.is_under_raid is True
        assert status.lockdown_active is True
        assert status.join_count_in_window == 12
        mock_redis.set.assert_called_once()
