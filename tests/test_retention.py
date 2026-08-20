"""Unit tests for DataRetentionWorker scheduled maintenance."""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import AuditLog, Chat, User, Warn
from services.cleaner.retention import DataRetentionWorker


@pytest.mark.asyncio
async def test_expire_old_warns(db_session: AsyncSession):
    """Verify that expired active warnings are deactivated by worker."""
    chat = Chat(chat_id=-100800, title="Retention Group")
    user = User(chat_id=-100800, telegram_id=444555, first_name="User1")
    db_session.add_all([chat, user])
    await db_session.commit()

    # Warn 1: Expired in the past
    past_date = datetime.now(timezone.utc) - timedelta(days=2)
    warn_expired = Warn(
        user_id=user.id,
        chat_id=chat.chat_id,
        reason="Old warn",
        expires_at=past_date,
        is_active=True,
    )

    # Warn 2: Active in the future
    future_date = datetime.now(timezone.utc) + timedelta(days=10)
    warn_active = Warn(
        user_id=user.id,
        chat_id=chat.chat_id,
        reason="Fresh warn",
        expires_at=future_date,
        is_active=True,
    )
    db_session.add_all([warn_expired, warn_active])
    await db_session.commit()

    expired_count = await DataRetentionWorker.expire_old_warns(db_session)
    await db_session.commit()

    assert expired_count == 1
    w1 = await db_session.get(Warn, warn_expired.id)
    w2 = await db_session.get(Warn, warn_active.id)
    assert w1.is_active is False
    assert w2.is_active is True


@pytest.mark.asyncio
async def test_purge_and_archive_logs(db_session: AsyncSession):
    """Verify that old audit log snippets are archived and purged from DB."""
    chat = Chat(chat_id=-100801, title="Archive Group")
    user = User(chat_id=-100801, telegram_id=555666, first_name="User2")
    db_session.add_all([chat, user])
    await db_session.commit()

    # Create old log entry (40 days old)
    old_date = datetime.now(timezone.utc) - timedelta(days=40)
    old_log = AuditLog(
        chat_id=chat.chat_id,
        user_id=user.id,
        action_type="delete",
        category="spam",
        reason="Old spam message",
        raw_message_snippet="Raw spam content that takes storage space",
    )
    db_session.add(old_log)
    await db_session.commit()

    # Manually set created_at to old date
    old_log.created_at = old_date
    await db_session.commit()

    archived_count = await DataRetentionWorker.purge_and_archive_logs(db_session, retention_days=30)
    await db_session.commit()

    assert archived_count == 1
    refreshed_log = await db_session.get(AuditLog, old_log.id)
    assert refreshed_log.raw_message_snippet is None
    assert refreshed_log.action_type == "delete"  # Statistics and record row preserved
