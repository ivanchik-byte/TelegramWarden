"""Unit tests for admin action callbacks and keyboards."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from bot.keyboards.admin_logs import get_admin_log_keyboard
from bot.handlers.admin_actions import handle_admin_false_positive, handle_admin_unban, handle_admin_ban_action, handle_admin_mute_action
from models import AuditLog, Chat, User


def test_admin_log_keyboard_ban_mode():
    """Verify log card keyboard for ban actions has unban and false positive buttons."""
    kb = get_admin_log_keyboard(chat_id=-1001, user_id=200, log_id=5, is_ban_action=True)
    assert len(kb.inline_keyboard) == 2
    assert kb.inline_keyboard[0][0].text == "Разбанить"
    assert kb.inline_keyboard[1][0].text == "Ложное срабатывание"


def test_admin_log_keyboard_warn_mode():
    """Verify log card keyboard for warn actions has unwarn, ban, and false positive buttons."""
    kb = get_admin_log_keyboard(chat_id=-1001, user_id=200, log_id=5, is_ban_action=False)
    assert len(kb.inline_keyboard) == 2
    assert kb.inline_keyboard[0][0].text == "Снять варн"
    assert kb.inline_keyboard[0][1].text == "Забанить навсегда"
    assert kb.inline_keyboard[1][0].text == "Ложное срабатывание"


@pytest.mark.asyncio
async def test_admin_false_positive_callback(db_session: AsyncSession):
    """Verify admin clicking false positive updates audit log record."""
    chat = Chat(chat_id=-100900, title="Security Group")
    user = User(chat_id=-100900, telegram_id=333222, first_name="Target")
    db_session.add_all([chat, user])
    await db_session.commit()

    log_entry = AuditLog(
        chat_id=chat.chat_id,
        user_id=user.id,
        action_type="warn",
        category="spam",
        reason="Test suspicion",
        confidence=85.0,
    )
    db_session.add(log_entry)
    await db_session.commit()

    # Mock callback query
    mock_callback = MagicMock()
    mock_callback.data = f"log:false_pos:{log_entry.id}"
    mock_callback.from_user.id = 999999
    mock_callback.from_user.first_name = "SuperAdmin"
    mock_callback.message.edit_reply_markup = AsyncMock()
    mock_callback.message.reply = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handle_admin_false_positive(callback=mock_callback, session=db_session)

    updated_log = await db_session.get(AuditLog, log_entry.id)
    assert updated_log.is_false_positive is True
    assert updated_log.reviewed_by_admin_id == 999999
    assert updated_log.admin_action_taken == "marked_false_positive"
    mock_callback.answer.assert_called_once()


@pytest.mark.asyncio
async def test_admin_ban_action_callback(db_session: AsyncSession):
    """Verify admin clicking ban action bans user and updates audit log record without import errors."""
    chat = Chat(chat_id=-100901, title="Security Group 2")
    user = User(chat_id=-100901, telegram_id=333223, first_name="Target User")
    db_session.add_all([chat, user])
    await db_session.commit()

    log_entry = AuditLog(
        chat_id=chat.chat_id,
        user_id=user.id,
        action_type="warn",
        category="spam",
        reason="Test suspicion",
        confidence=85.0,
    )
    db_session.add(log_entry)
    await db_session.commit()

    mock_callback = MagicMock()
    mock_callback.data = f"log:ban:{-100901}:{333223}:{log_entry.id}"
    mock_callback.bot = AsyncMock()
    mock_callback.bot.ban_chat_member = AsyncMock()
    mock_callback.from_user.id = 999999
    mock_callback.from_user.first_name = "SuperAdmin"
    mock_callback.message.edit_reply_markup = AsyncMock()
    mock_callback.message.reply = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handle_admin_ban_action(callback=mock_callback, session=db_session)

    updated_log = await db_session.get(AuditLog, log_entry.id)
    assert updated_log.reviewed_by_admin_id == 999999
    assert updated_log.admin_action_taken == "banned_by_admin"
    mock_callback.bot.ban_chat_member.assert_called_once()


@pytest.mark.asyncio
async def test_admin_mute_action_callback(db_session: AsyncSession):
    """Verify admin clicking mute action mutes user and updates audit log record without import errors."""
    chat = Chat(chat_id=-100902, title="Security Group 3")
    user = User(chat_id=-100902, telegram_id=333224, first_name="Target Mute User")
    db_session.add_all([chat, user])
    await db_session.commit()

    log_entry = AuditLog(
        chat_id=chat.chat_id,
        user_id=user.id,
        action_type="warn",
        category="spam",
        reason="Test suspicion",
        confidence=85.0,
    )
    db_session.add(log_entry)
    await db_session.commit()

    mock_callback = MagicMock()
    mock_callback.data = f"log:mute:{-100902}:{333224}:{log_entry.id}"
    mock_callback.bot = AsyncMock()
    mock_callback.bot.restrict_chat_member = AsyncMock()
    mock_callback.from_user.id = 999999
    mock_callback.from_user.first_name = "SuperAdmin"
    mock_callback.message.edit_reply_markup = AsyncMock()
    mock_callback.message.reply = AsyncMock()
    mock_callback.answer = AsyncMock()

    await handle_admin_mute_action(callback=mock_callback, session=db_session)

    updated_log = await db_session.get(AuditLog, log_entry.id)
    assert updated_log.reviewed_by_admin_id == 999999
    assert updated_log.admin_action_taken == "muted_by_admin"
    mock_callback.bot.restrict_chat_member.assert_called_once()
