"""End-to-end tests for Jev Tier-1 triage wired into AIClientDispatcher."""

import json

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock

from services.ai.client import AIClientDispatcher
from services.ai.jev_client import JevClient
from services.ai.schema import SuggestedAction, ViolationCategory


def _jev_answer(noul: float, choice: str, probs: dict) -> httpx.Response:
    return httpx.Response(200, json={
        "model": "jev-1.13.0",
        "answers": {
            "is_violation": {"type": "noul", "noul": noul},
            "category": {"type": "choice", "choice": choice, "confidence": 0.9, "probabilities": probs},
        },
        "usage": {"input_tokens": 1284, "output_tokens": 0, "cost_usd": 0.0000539},
    })


def _jev_client(handler) -> JevClient:
    return JevClient(
        api_key="test-key",
        base_url="https://api.typesafe.ai",
        model="jev-1.13.0",
        transport=httpx.MockTransport(handler),
    )


def _llm_verdict_response() -> MagicMock:
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps({
        "is_violation": True,
        "category": "crypto_scam",
        "confidence": 90.0,
        "reason": "Крипто-скам",
        "suggested_action": "ban_user",
    })
    mock_response.choices = [mock_choice]
    return mock_response


def _dispatcher_with_jev(handler) -> AIClientDispatcher:
    dispatcher = AIClientDispatcher()
    dispatcher.jev_client = _jev_client(handler)
    dispatcher.primary_client.chat.completions.create = AsyncMock(
        return_value=_llm_verdict_response()
    )
    return dispatcher

@pytest.mark.asyncio
async def test_triage_parses_clean_answer():
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url.path == "/v1/systemone"
        assert body["model"] == "jev-1.13.0"
        assert body["state"] == {"messages": {"m0": {"text": "привет"}}}
        assert set(body["questions"]) == {"is_violation", "category"}
        return _jev_answer(0.012, "clean", {"clean": 0.98, "commercial_ad": 0.02})

    client = _jev_client(handler)
    try:
        result = await client.triage("привет")
    finally:
        await client.aclose()
    assert result is not None
    assert result.is_violation_prob == 0.012
    assert result.top_category == "clean"
    assert result.latency_ms >= 0.0


@pytest.mark.asyncio
@pytest.mark.parametrize("status,headers", [(429, {"Retry-After": "5"}), (529, {}), (500, {})])
async def test_triage_transient_failures_fall_through(status, headers):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, headers=headers, json={})

    client = _jev_client(handler)
    assert await client.triage("текст") is None


@pytest.mark.asyncio
async def test_triage_timeout_falls_through():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("down")

    client = _jev_client(handler)
    assert await client.triage("текст") is None


@pytest.mark.asyncio
async def test_triage_401_disables_tier():
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(401, json={"error": {"code": "invalid_api_key"}})

    client = _jev_client(handler)
    assert await client.triage("текст") is None
    assert await client.triage("текст") is None
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_triage_429_freezes_until_retry_after():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "120"}, json={})

    client = _jev_client(handler)
    assert await client.triage("текст") is None
    assert client._frozen_until > 0


@pytest.mark.asyncio
async def test_fast_pass_clean_skips_llm():
    async def handler(request: httpx.Request) -> httpx.Response:
        return _jev_answer(0.012, "clean", {"clean": 0.99})

    dispatcher = _dispatcher_with_jev(handler)
    verdict = await dispatcher.analyze_message("привет, как дела?")

    assert verdict.is_violation is False
    assert verdict.triaged_by_jev is True
    assert verdict.jev_latency_ms is not None
    assert "[Jev Fast-Pass]" in verdict.reason
    dispatcher.primary_client.chat.completions.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_borderline_prob_escalates_with_hint_in_prompt():
    seen_prompts = []

    async def jev_handler(request: httpx.Request) -> httpx.Response:
        return _jev_answer(0.05, "commercial_ad", {"commercial_ad": 0.4, "clean": 0.6})

    dispatcher = _dispatcher_with_jev(jev_handler)

    async def capture_create(**kwargs):
        seen_prompts.append(kwargs["messages"][1]["content"])
        return _llm_verdict_response()

    dispatcher.primary_client.chat.completions.create = AsyncMock(side_effect=capture_create)
    verdict = await dispatcher.analyze_message("ребят, посоветуйте канал")

    assert verdict.is_violation is True
    assert verdict.triaged_by_jev is True
    assert "Preliminary triage hint from fast classifier: commercial_ad (5%)" in seen_prompts[0]


@pytest.mark.asyncio
async def test_critical_category_mass_forces_escalation():
    async def handler(request: httpx.Request) -> httpx.Response:
        return _jev_answer(0.01, "clean", {"clean": 0.97, "phishing": 0.02})

    dispatcher = _dispatcher_with_jev(handler)
    verdict = await dispatcher.analyze_message("проверьте ваш аккаунт")

    assert verdict.is_violation is True
    assert verdict.triaged_by_jev is True
    dispatcher.primary_client.chat.completions.create.assert_awaited()


@pytest.mark.asyncio
async def test_hidden_entities_block_fast_pass():
    async def handler(request: httpx.Request) -> httpx.Response:
        return _jev_answer(0.012, "clean", {"clean": 0.99})

    dispatcher = _dispatcher_with_jev(handler)
    verdict = await dispatcher.analyze_message(
        "невинный текст", has_hidden_entities=True
    )

    assert verdict.triaged_by_jev is True
    dispatcher.primary_client.chat.completions.create.assert_awaited()


@pytest.mark.asyncio
async def test_jev_outage_falls_back_to_deepseek_then_groq():
    async def jev_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    dispatcher = AIClientDispatcher()
    dispatcher.jev_client = _jev_client(jev_handler)
    dispatcher.primary_client.chat.completions.create = AsyncMock(
        side_effect=Exception("DeepSeek down")
    )
    fallback = MagicMock()
    fallback.chat.completions.create = AsyncMock(return_value=_llm_verdict_response())
    dispatcher.fallback_client = fallback

    verdict = await dispatcher.analyze_message("раздача usdt")
    assert verdict.is_violation is True
    assert verdict.triaged_by_jev is False
    fallback.chat.completions.create.assert_awaited()


@pytest.mark.asyncio
async def test_total_outage_still_fails_open_clean():
    async def jev_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    dispatcher = AIClientDispatcher()
    dispatcher.jev_client = _jev_client(jev_handler)
    dispatcher.primary_client.chat.completions.create = AsyncMock(
        side_effect=Exception("all down")
    )
    dispatcher.fallback_client = None

    verdict = await dispatcher.analyze_message("раздача usdt")
    assert verdict.is_violation is False
    assert verdict.fail_open is True


def test_dispatcher_without_key_has_no_jev_tier():
    dispatcher = AIClientDispatcher.__new__(AIClientDispatcher)
    assert getattr(dispatcher, "jev_client", None) is None
