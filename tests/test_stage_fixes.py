"""Regression tests for review-driven fixes (sampling, NaN, guards, schema bounds)."""

import pytest
from datetime import datetime, timezone
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock

from api.auth import TelegramUser, get_current_telegram_user
from api.main import app
from bot.utils.sanctions import SanctionsExecutor
from core.database import get_db_session
from models import AuditLog, Chat, User
from services.ai.client import AIClientDispatcher, normalize_confidence
from services.ai.normalizer import TextSanitizer
from services.ai.risk_scorer import RiskScorer
from services.moderation.night_mode import _parse_hhmm

import json


def _verdict_payload(payload: dict) -> MagicMock:
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(payload)
    mock_response.choices = [mock_choice]
    return mock_response


def test_zero_sampling_rate_disables_sampling():
    """sampling_rate=0 must mean 'never sample', not the default cadence."""
    assert RiskScorer.cadence_from_rate(0.0) is None
    assert RiskScorer.cadence_from_rate(-0.5) is None

    sanitized = TextSanitizer.sanitize("обычное чистое сообщение")
    result = RiskScorer.evaluate(
        sanitized=sanitized,
        user_message_count=20,
        user_days_in_chat=45,
        telegram_id=40,
        sampling_rate=0.0,
    )
    assert result.should_call_ai is False
    assert result.trigger_reasons == []


def test_non_finite_confidence_takes_unknown_path():
    """NaN/inf from the model must not become NaN verdicts or fail-open CLEAN."""
    import math

    with pytest.raises(ValueError):
        normalize_confidence(math.nan)
    with pytest.raises(ValueError):
        normalize_confidence(math.inf)


@pytest.mark.asyncio
async def test_nan_confidence_violation_stays_flagged_below_thresholds():
    """A claimed violation with NaN certainty keeps the flag at 1%, never NaN."""
    dispatcher = AIClientDispatcher()
    dispatcher.primary_client.chat.completions.create = AsyncMock(
        return_value=_verdict_payload({
            "is_violation": True,
            "category": "crypto_scam",
            "confidence": float("nan"),
            "reason": "Скам",
            "suggested_action": "ban_user",
        })
    )

    verdict = await dispatcher.analyze_message("раздача usdt")
    assert verdict.is_violation is True
    assert verdict.confidence == 1.0


def test_parse_hhmm_rejects_seconds():
    assert _parse_hhmm("12:00:00") is None
    assert _parse_hhmm("23:00") == (23, 0)


@pytest.mark.asyncio
async def test_apply_warn_with_null_limit_uses_default(db_session: AsyncSession):
    """NULL warn_limit in legacy rows must not raise TypeError."""
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock()

    chat = Chat(chat_id=-100444, title="Legacy Chat", warn_limit=None)
    user = User(chat_id=-100444, telegram_id=555, first_name="Legacy")
    db_session.add_all([chat, user])
    await db_session.commit()

    active = await SanctionsExecutor.apply_warn(
        bot=mock_bot, session=db_session, chat_db=chat, user_db=user, reason="Спам"
    )
    assert active == 1


@pytest.mark.asyncio
async def test_mute_clamps_negative_duration(db_session: AsyncSession):
    """Negative mute durations must not produce until_date in the past."""
    mock_bot = MagicMock()
    mock_bot.restrict_chat_member = AsyncMock()

    user = User(chat_id=-100555, telegram_id=666, first_name="Spammer")
    db_session.add(user)
    await db_session.commit()

    ok = await SanctionsExecutor.mute_user(
        bot=mock_bot, session=db_session, chat_id=-100555, user_db=user,
        duration_minutes=-30, reason="Спам",
    )
    assert ok is True
    assert user.is_muted is True
    assert user.muted_until > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_patch_rejects_invalid_enum_and_bounds(db_session: AsyncSession):
    chat = Chat(chat_id=-100666, title="Bounded", whitelisted_users=[999])
    db_session.add(chat)
    await db_session.commit()

    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_current_telegram_user] = lambda: TelegramUser(id=999, first_name="Admin")

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.patch("/api/chats/-100666", json={"moderation_mode": "foo"})
            assert res.status_code == 422

            res = await client.patch("/api/chats/-100666", json={"captcha_timeout_seconds": 999999})
            assert res.status_code == 422

            res = await client.patch("/api/chats/-100666", json={"warn_punishment": "kick"})
            assert res.status_code == 422

            res = await client.patch("/api/chats/-100666", json={"night_mode_start": "25:99"})
            assert res.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_stats_aggregation_counts_mutes_and_false_positives(db_session: AsyncSession):
    chat = Chat(chat_id=-100777, title="Aggro", whitelisted_users=[999])
    user = User(chat_id=-100777, telegram_id=111, first_name="Off")
    db_session.add_all([chat, user])
    await db_session.commit()

    db_session.add_all([
        AuditLog(chat_id=-100777, user_id=user.id, action_type="mute_user", category="flood_spam", reason="F", confidence=80.0),
        AuditLog(chat_id=-100777, user_id=user.id, action_type="warn", category="toxic_insult", reason="T", confidence=60.0, is_false_positive=True),
    ])
    await db_session.commit()

    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_current_telegram_user] = lambda: TelegramUser(id=999, first_name="Admin")

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/stats/-100777")
            assert res.status_code == 200
            data = res.json()
            assert data["total_violations"] == 2
            assert data["total_mutes"] == 1
            assert data["false_positives_count"] == 1
    finally:
        app.dependency_overrides.clear()
