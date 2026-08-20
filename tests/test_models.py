"""Unit tests for SQLAlchemy database models and relationships."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Chat, User, Warn, AuditLog


@pytest.mark.asyncio
async def test_chat_creation_and_defaults(db_session: AsyncSession):
    """Verify Chat model creation, default values, and JSON fields."""
    chat = Chat(
        chat_id=-1001234567890,
        title="Test Security Community",
        captcha_enabled=True,
        captcha_type="button",
        ai_confidence_threshold=88.5,
        whitelisted_bots=["@vote", "@like"],
    )
    db_session.add(chat)
    await db_session.commit()

    result = await db_session.execute(select(Chat).where(Chat.chat_id == -1001234567890))
    saved_chat = result.scalar_one_or_none()

    assert saved_chat is not None
    assert saved_chat.title == "Test Security Community"
    assert saved_chat.captcha_enabled is True
    assert saved_chat.ai_confidence_threshold == 88.5
    assert "@vote" in saved_chat.whitelisted_bots
    assert saved_chat.clean_service_messages is True


@pytest.mark.asyncio
async def test_user_reputation_and_relationships(db_session: AsyncSession):
    """Verify User model creation, relationship with Chat, and reputation stats."""
    chat = Chat(chat_id=-100999, title="Alpha Group")
    db_session.add(chat)
    await db_session.commit()

    user = User(
        telegram_id=777888999,
        chat_id=-100999,
        username="cool_dev",
        first_name="Ivan",
        reputation_score=100,
    )
    db_session.add(user)
    await db_session.commit()

    result = await db_session.execute(
        select(User).where(User.telegram_id == 777888999, User.chat_id == -100999)
    )
    saved_user = result.scalar_one_or_none()

    assert saved_user is not None
    assert saved_user.username == "cool_dev"
    assert saved_user.reputation_score == 100
    assert saved_user.is_banned is False
    assert saved_user.total_violations_count == 0


@pytest.mark.asyncio
async def test_warn_creation_and_expiration(db_session: AsyncSession):
    """Verify Warn creation with auto-calculated expiration date."""
    chat = Chat(chat_id=-100888, title="Beta Group")
    user = User(telegram_id=111222, chat_id=-100888, first_name="Spammer")
    db_session.add_all([chat, user])
    await db_session.commit()

    warn = Warn(
        user_id=user.id,
        chat_id=chat.chat_id,
        reason="Реклама несанкционированных каналов",
        category="ad",
    )
    db_session.add(warn)
    await db_session.commit()

    result = await db_session.execute(select(Warn).where(Warn.user_id == user.id))
    saved_warn = result.scalar_one_or_none()

    assert saved_warn is not None
    assert saved_warn.category == "ad"
    assert saved_warn.is_active is True
    assert saved_warn.expires_at > saved_warn.created_at


@pytest.mark.asyncio
async def test_audit_log_and_feedback(db_session: AsyncSession):
    """Verify AuditLog records, false positive marking, and feedback."""
    chat = Chat(chat_id=-100777, title="Gamma Group")
    user = User(telegram_id=333444, chat_id=-100777, first_name="Target")
    db_session.add_all([chat, user])
    await db_session.commit()

    audit_entry = AuditLog(
        chat_id=chat.chat_id,
        user_id=user.id,
        action_type="delete_and_warn",
        category="crypto_scam",
        reason="Подозрительный призыв инвестировать в личку",
        confidence=91.4,
        raw_message_snippet="Пиши в лс за подробностями доходности",
    )
    db_session.add(audit_entry)
    await db_session.commit()

    result = await db_session.execute(
        select(AuditLog).where(AuditLog.chat_id == chat.chat_id)
    )
    saved_log = result.scalar_one_or_none()

    assert saved_log is not None
    assert saved_log.confidence == 91.4
    assert saved_log.is_false_positive is False

    # Simulate admin marking false positive
    saved_log.is_false_positive = True
    saved_log.admin_action_taken = "unbanned"
    saved_log.reviewed_by_admin_id = 999000111
    await db_session.commit()

    updated = await db_session.get(AuditLog, saved_log.id)
    assert updated.is_false_positive is True
    assert updated.admin_action_taken == "unbanned"
