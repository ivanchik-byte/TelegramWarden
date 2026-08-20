"""Unit tests for SanctionsExecutor warning escalation and penalties."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from bot.utils.sanctions import SanctionsExecutor
from models import Chat, User, Warn


@pytest.mark.asyncio
async def test_apply_warn_single_warning(db_session: AsyncSession):
    """Verify single warning issuance without reaching punishment limit."""
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()

    chat = Chat(chat_id=-100111, title="Test Chat", warn_limit=3)
    user = User(chat_id=-100111, telegram_id=999, first_name="Alex")
    db_session.add_all([chat, user])
    await db_session.commit()

    active_warns = await SanctionsExecutor.apply_warn(
        bot=mock_bot,
        session=db_session,
        chat_db=chat,
        user_db=user,
        reason="Ненормативная лексика",
        category="toxic",
    )

    assert active_warns == 1
    assert user.total_violations_count == 1
    assert user.reputation_score == 85
    mock_bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_apply_warn_escalation_to_mute(db_session: AsyncSession):
    """Verify automatic mute escalation when user reaches warn limit (3/3)."""
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()
    mock_bot.restrict_chat_member = AsyncMock()

    chat = Chat(chat_id=-100222, title="Strict Chat", warn_limit=2, warn_punishment="mute")
    user = User(chat_id=-100222, telegram_id=888, first_name="Repeater")
    db_session.add_all([chat, user])
    await db_session.commit()

    # Warn 1
    await SanctionsExecutor.apply_warn(
        bot=mock_bot, session=db_session, chat_db=chat, user_db=user, reason="Реклама"
    )
    # Warn 2 (reaches limit 2/2 -> triggers mute)
    await SanctionsExecutor.apply_warn(
        bot=mock_bot, session=db_session, chat_db=chat, user_db=user, reason="Реклама повторно"
    )

    assert user.is_muted is True
    assert user.muted_until is not None
    mock_bot.restrict_chat_member.assert_called_once()


@pytest.mark.asyncio
async def test_ban_user_execution(db_session: AsyncSession):
    """Verify permanent ban execution and database status update."""
    mock_bot = MagicMock()
    mock_bot.ban_chat_member = AsyncMock()
    mock_bot.send_message = AsyncMock()

    user = User(chat_id=-100333, telegram_id=777, first_name="Scammer")
    db_session.add(user)
    await db_session.commit()

    banned = await SanctionsExecutor.ban_user(
        bot=mock_bot,
        session=db_session,
        chat_id=-100333,
        user_db=user,
        reason="Крипто-фишинг",
    )

    assert banned is True
    assert user.is_banned is True
    assert user.ban_reason == "Крипто-фишинг"
    mock_bot.ban_chat_member.assert_called_once()
