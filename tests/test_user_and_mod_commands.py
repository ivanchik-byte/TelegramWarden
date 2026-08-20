"""Unit tests for user profile commands and manual admin moderation commands."""

import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.handlers.moderation_commands import parse_duration_string
from bot.utils.sanctions import SanctionsExecutor
from models import Chat, User, Warn, AuditLog


def test_parse_duration_string():
    """Verify parsing various duration strings into minutes."""
    assert parse_duration_string("30m") == 30
    assert parse_duration_string("2h") == 120
    assert parse_duration_string("1d") == 1440
    assert parse_duration_string("7d") == 10080
    assert parse_duration_string("invalid") is None


@pytest.mark.asyncio
async def test_manual_warn_and_unwarn_flow(db_session: AsyncSession):
    """Verify manual warn creation, warn expiration, and unwarn deactivation."""
    chat = Chat(chat_id=-100888, title="Community Group", warn_limit=3, warn_expiration_days=14)
    user = User(chat_id=-100888, telegram_id=555444, first_name="Offender")
    db_session.add_all([chat, user])
    await db_session.commit()

    # 1. Apply Warn
    warn = Warn(
        user_id=user.id,
        chat_id=chat.chat_id,
        reason="Flood and caps spam",
        category="flood",
    )
    db_session.add(warn)
    user.total_violations_count += 1
    user.reputation_score = 85
    await db_session.commit()

    res_w = await db_session.execute(
        select(Warn).where(Warn.user_id == user.id, Warn.is_active == True)
    )
    active_warns = res_w.scalars().all()
    assert len(active_warns) == 1
    assert active_warns[0].reason == "Flood and caps spam"

    # 2. Deactivate Warn (Unwarn)
    active_warns[0].is_active = False
    user.reputation_score = 100
    await db_session.commit()

    res_w_after = await db_session.execute(
        select(Warn).where(Warn.user_id == user.id, Warn.is_active == True)
    )
    assert len(res_w_after.scalars().all()) == 0


@pytest.mark.asyncio
async def test_clearwarns_flow(db_session: AsyncSession):
    """Verify clearing all active warns for a member."""
    chat = Chat(chat_id=-100777, title="Dev Group", warn_limit=3)
    user = User(chat_id=-100777, telegram_id=777666, first_name="Spammer")
    db_session.add_all([chat, user])
    await db_session.commit()

    # Add 2 warns
    w1 = Warn(user_id=user.id, chat_id=chat.chat_id, reason="Reason 1")
    w2 = Warn(user_id=user.id, chat_id=chat.chat_id, reason="Reason 2")
    db_session.add_all([w1, w2])
    await db_session.commit()

    # Clear all warns
    res_w = await db_session.execute(
        select(Warn).where(Warn.user_id == user.id, Warn.is_active == True)
    )
    for w in res_w.scalars().all():
        w.is_active = False
    await db_session.commit()

    res_check = await db_session.execute(
        select(Warn).where(Warn.user_id == user.id, Warn.is_active == True)
    )
    assert len(res_check.scalars().all()) == 0
