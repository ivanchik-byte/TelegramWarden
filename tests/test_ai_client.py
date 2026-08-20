"""Unit tests for AIClientDispatcher and structured JSON output validation."""

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
    assert verdict.confidence == 92.0
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
