"""Unit tests for superadmin authentication and dynamic whitelist management."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from bot.utils.admin_checker import is_chat_admin, is_superadmin
from core.config import settings
from models import Chat


def test_superadmin_parsing_from_config():
    """Verify comma-separated SUPERADMIN_IDS string parses into integer list."""
    with patch.object(settings, "SUPERADMIN_IDS", "111222, 333444, 555666"):
        admins = settings.superadmin_id_list
        assert admins == [111222, 333444, 555666]
        assert is_superadmin(111222) is True
        assert is_superadmin(999999) is False


@pytest.mark.asyncio
async def test_is_chat_admin_superadmin_bypass():
    """Verify superadmin automatically passes chat admin check without API call."""
    mock_bot = MagicMock()
    with patch.object(settings, "SUPERADMIN_IDS", "777888"):
        result = await is_chat_admin(mock_bot, chat_id=-1001, user_id=777888)
        assert result is True
        mock_bot.get_chat_member.assert_not_called()


@pytest.mark.asyncio
async def test_is_chat_admin_whitelist(db_session: AsyncSession):
    """Verify whitelisted user in chat DB passes admin check."""
    chat = Chat(chat_id=-100999, title="Whitelist Group", whitelisted_users=[444555])
    mock_bot = MagicMock()

    result = await is_chat_admin(mock_bot, chat_id=-100999, user_id=444555, chat_db=chat)
    assert result is True
    mock_bot.get_chat_member.assert_not_called()


@pytest.mark.asyncio
async def test_is_chat_admin_telegram_status():
    """Verify regular Telegram administrator status check via Bot API."""
    mock_bot = MagicMock()
    mock_member = MagicMock()
    mock_member.status = "administrator"
    mock_bot.get_chat_member = AsyncMock(return_value=mock_member)

    result = await is_chat_admin(mock_bot, chat_id=-100555, user_id=123123)
    assert result is True
    mock_bot.get_chat_member.assert_called_once_with(chat_id=-100555, user_id=123123)
