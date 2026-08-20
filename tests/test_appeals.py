"""Unit tests for user appeals and group /report command."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from bot.handlers.appeals import handle_appeal_accept
from models import AuditLog, Chat, User, Warn


@pytest.mark.asyncio
async def test_appeal_accept_flow(db_session: AsyncSession):
    """Verify admin approval clears user warns and issues unban."""
    chat = Chat(chat_id=-100777, title="Appeals Group")
    user = User(telegram_id=888999, chat_id=-100777, username="appealer")
    db_session.add_all([chat, user])
    await db_session.flush()

    warn = Warn(user_id=user.id, chat_id=-100777, reason="Testing warn", category="spam")
    audit = AuditLog(chat_id=-100777, user_id=user.id, action_type="warn", category="spam", reason="test")
    db_session.add_all([warn, audit])
    await db_session.commit()

    # Mock callback
    mock_callback = MagicMock()
    mock_callback.data = f"appeal:accept:-100777:888999:{audit.id}"
    mock_callback.from_user.id = 8667615215  # Superadmin ID
    mock_callback.from_user.full_name = "SuperAdmin"
    mock_callback.bot.unban_chat_member = AsyncMock()
    mock_callback.message.edit_text = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handle_appeal_accept(mock_callback, db_session)

    mock_callback.bot.unban_chat_member.assert_called_once_with(
        chat_id=-100777,
        user_id=888999,
        only_if_banned=True,
    )
    mock_callback.message.edit_text.assert_called_once()
