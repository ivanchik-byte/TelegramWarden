"""Unit tests for RiskScorer 0-token heuristic evaluation."""

from services.ai.normalizer import TextSanitizer
from services.ai.risk_scorer import RiskScorer


def test_clean_message_from_established_user_passes_zero_tokens():
    """Verify that normal conversation from established members bypasses LLM (0 tokens)."""
    sanitized = TextSanitizer.sanitize("Привет всем, отличная погода сегодня!")
    score_result = RiskScorer.evaluate(
        sanitized=sanitized,
        user_message_count=150,
        user_days_in_chat=45,
        sampling_rate=0.0,  # disable sampling for deterministic test
    )

    assert score_result.should_call_ai is False
    assert score_result.risk_score == 0
    assert len(score_result.trigger_reasons) == 0


def test_newcomer_with_links_triggers_ai():
    """Verify that newcomers sending links accumulate high risk score and trigger AI."""
    sanitized = TextSanitizer.sanitize("Посмотрите полезный сайт https://example.com/info")
    score_result = RiskScorer.evaluate(
        sanitized=sanitized,
        user_message_count=1,
        user_days_in_chat=0,
    )

    assert score_result.should_call_ai is True
    assert score_result.risk_score >= 70
    assert any("contains_urls" in r for r in score_result.trigger_reasons)
    assert "newcomer_activity" in score_result.trigger_reasons


def test_high_risk_crypto_keywords_trigger_ai():
    """Verify that messages with crypto scam keywords trigger AI even without links."""
    sanitized = TextSanitizer.sanitize("Раздача TON и высокий доход на пассиве")
    score_result = RiskScorer.evaluate(
        sanitized=sanitized,
        user_message_count=50,
        user_days_in_chat=20,
    )

    assert score_result.should_call_ai is True
    assert any("keywords_matched" in r for r in score_result.trigger_reasons)
