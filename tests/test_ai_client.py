"""Unit tests for AIClientDispatcher and structured JSON output validation."""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock
from services.ai.client import AIClientDispatcher
from services.ai.schema import (
    AIModerationVerdict,
    SuggestedAction,
    ViolationCategory,
)


@pytest.mark.asyncio
async def test_ai_dispatcher_successful_primary_parse():
    """Verify that structured JSON from Primary Provider is parsed into Pydantic model."""
    dispatcher = AIClientDispatcher()

    # Mock primary client response
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = """
    {
        "is_violation": true,
        "category": "crypto_scam",
        "confidence": 97.5,
        "reason": "Завуалированный крипто-скам и призыв в ЛС",
        "suggested_action": "ban_user"
    }
    """
    mock_response.choices = [mock_choice]

    dispatcher.primary_client.chat.completions.create = AsyncMock(return_value=mock_response)

    verdict = await dispatcher.analyze_message("Ребята, раздача 100 USDT, пишите в лс")

    assert isinstance(verdict, AIModerationVerdict)
    assert verdict.is_violation is True
    assert verdict.category == ViolationCategory.CRYPTO_SCAM
    assert verdict.confidence == 97.5
    assert verdict.suggested_action == SuggestedAction.BAN_USER


@pytest.mark.asyncio
async def test_ai_dispatcher_fallback_on_primary_failure():
    """Verify that dispatcher automatically falls back to secondary provider upon primary error."""
    dispatcher = AIClientDispatcher()

    # Make primary fail
    dispatcher.primary_client.chat.completions.create = AsyncMock(
        side_effect=Exception("DeepSeek API Timeout")
    )

    # Setup fallback client
    mock_fallback_client = MagicMock()
    mock_fallback_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = """
    {
        "is_violation": true,
        "category": "commercial_ad",
        "confidence": 92.0,
        "reason": "Несогласованная реклама канала",
        "suggested_action": "warn"
    }
    """
    mock_fallback_response.choices = [mock_choice]
    mock_fallback_client.chat.completions.create = AsyncMock(return_value=mock_fallback_response)

    dispatcher.fallback_client = mock_fallback_client

    verdict = await dispatcher.analyze_message("Подписывайся на t.me/my_channel")

    assert verdict.is_violation is True
    assert verdict.category == ViolationCategory.COMMERCIAL_AD
    assert verdict.confidence == 84.0  # commercial_ad ceiling clamp
    assert verdict.suggested_action == SuggestedAction.WARN


@pytest.mark.asyncio
async def test_ai_dispatcher_fail_open_on_total_failure():
    """Verify that dispatcher fails open with clean verdict when all providers fail."""
    dispatcher = AIClientDispatcher()
    dispatcher.primary_client.chat.completions.create = AsyncMock(
        side_effect=Exception("Primary Down")
    )
    dispatcher.fallback_client = None

    verdict = await dispatcher.analyze_message("Some text")

    assert verdict.is_violation is False
    assert verdict.category == ViolationCategory.CLEAN
    assert verdict.confidence == 0.0
    assert verdict.suggested_action == SuggestedAction.PASS_MESSAGE


def _make_verdict_response(payload: dict) -> MagicMock:
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(payload)
    mock_response.choices = [mock_choice]
    return mock_response


@pytest.mark.asyncio
async def test_calibration_extreme_confidence_is_clamped_to_category_band():
    """LLM habit extremes (99%) must be clamped: toxic/commercial stay below ban threshold."""
    dispatcher = AIClientDispatcher()

    dispatcher.primary_client.chat.completions.create = AsyncMock(
        return_value=_make_verdict_response({
            "is_violation": True,
            "category": "toxic_insult",
            "confidence": 99.0,
            "reason": "Оскорбление участника",
            "suggested_action": "warn",
        })
    )

    verdict = await dispatcher.analyze_message("ты урод")

    assert verdict.category == ViolationCategory.TOXIC_INSULT
    assert verdict.confidence == 84.0
    # Confidence-based ban tier (>=85 by default) is unreachable for warn-tier categories.
    assert verdict.confidence < 85.0


@pytest.mark.asyncio
async def test_calibration_clean_high_confidence_stays_low_threat():
    """A clean verdict with high model certainty maps to low threat risk without inversion."""
    dispatcher = AIClientDispatcher()

    dispatcher.primary_client.chat.completions.create = AsyncMock(
        return_value=_make_verdict_response({
            "is_violation": False,
            "category": "clean",
            "confidence": 87.0,
            "reason": "Обычное сообщение",
            "suggested_action": "pass_message",
        })
    )

    verdict = await dispatcher.analyze_message("привет, как дела?")

    assert verdict.is_violation is False
    assert verdict.confidence <= 15.0
    assert verdict.suggested_action == SuggestedAction.PASS_MESSAGE


@pytest.mark.asyncio
async def test_calibration_mid_range_values_pass_through_unchanged():
    """Values inside the category band keep the model's relative granularity."""
    dispatcher = AIClientDispatcher()

    dispatcher.primary_client.chat.completions.create = AsyncMock(
        return_value=_make_verdict_response({
            "is_violation": True,
            "category": "crypto_scam",
            "confidence": 62.0,
            "reason": "Подозрительное предложение заработка",
            "suggested_action": "delete_message",
        })
    )

    verdict = await dispatcher.analyze_message("кто хочет поднять бабок?")

    assert verdict.category == ViolationCategory.CRYPTO_SCAM
    assert verdict.confidence == 62.0


@pytest.mark.asyncio
async def test_calibration_unsure_contraband_is_not_clamped_up():
    """A low-confidence contraband guess must never be inflated into the ban tier."""
    dispatcher = AIClientDispatcher()

    dispatcher.primary_client.chat.completions.create = AsyncMock(
        return_value=_make_verdict_response({
            "is_violation": True,
            "category": "illegal_contraband",
            "confidence": 30.0,
            "reason": "Похоже на обсуждение запрещённых веществ, но контекст неясен",
            "suggested_action": "delete_message",
        })
    )

    verdict = await dispatcher.analyze_message("где взять то что обсуждали?")

    assert verdict.category == ViolationCategory.ILLEGAL_CONTRABAND
    assert verdict.confidence == 30.0
    assert verdict.confidence < 85.0


@pytest.mark.asyncio
async def test_unknown_category_from_llm_maps_to_other_violation():
    """A hallucinated category must not discard the verdict via ValidationError."""
    dispatcher = AIClientDispatcher()

    dispatcher.primary_client.chat.completions.create = AsyncMock(
        return_value=_make_verdict_response({
            "is_violation": True,
            "category": "scam",
            "confidence": 80.0,
            "reason": "Мошенничество",
            "suggested_action": "warn",
        })
    )

    verdict = await dispatcher.analyze_message("переведи мне 500 рублей и получи вдвое больше")

    # Verdict preserved, category degraded gracefully instead of fail-open clean
    assert verdict.is_violation is True
    assert verdict.category == ViolationCategory.OTHER_VIOLATION


@pytest.mark.asyncio
async def test_unknown_suggested_action_falls_back_to_warn():
    """A hallucinated suggested_action must degrade to a safe default, not crash parsing."""
    dispatcher = AIClientDispatcher()

    dispatcher.primary_client.chat.completions.create = AsyncMock(
        return_value=_make_verdict_response({
            "is_violation": True,
            "category": "toxic_insult",
            "confidence": 70.0,
            "reason": "Оскорбление участника",
            "suggested_action": "nuke_user",
        })
    )

    verdict = await dispatcher.analyze_message("ты никто и звать тебя никак")

    assert verdict.is_violation is True
    assert verdict.suggested_action == SuggestedAction.WARN
