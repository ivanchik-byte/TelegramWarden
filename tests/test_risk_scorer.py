"""Unit tests for RiskScorer 0-token heuristic evaluation."""

from services.ai.normalizer import TextSanitizer
from services.ai.risk_scorer import RiskScorer


def test_clean_message_from_established_user_passes_zero_tokens():
    """Verify that normal conversation from established members bypasses LLM (0 tokens)."""
    sanitized = TextSanitizer.sanitize("Привет всем, отличная погода сегодня!")
    score_result = RiskScorer.evaluate(
        sanitized=sanitized,
        user_message_count=151,  # not on the sampling cadence
        user_days_in_chat=45,
    )

    assert score_result.should_call_ai is False
    assert score_result.risk_score == 0
    assert len(score_result.trigger_reasons) == 0


def test_scheduled_sampling_fires_on_cadence_for_any_length():
    """Every N-th message is inspected deterministically — long messages included."""
    sanitized_long = TextSanitizer.sanitize("Обычный длинный текст без единого триггера. " * 8)
    result_long = RiskScorer.evaluate(
        sanitized=sanitized_long,
        user_message_count=160,
        user_days_in_chat=45,
    )
    assert result_long.should_call_ai is True
    assert "scheduled_sampling_check" in result_long.trigger_reasons

    sanitized_short = TextSanitizer.sanitize("ок")
    result_short = RiskScorer.evaluate(
        sanitized=sanitized_short,
        user_message_count=40,
        user_days_in_chat=45,
    )
    assert result_short.should_call_ai is True


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


def test_cyrillic_keywords_match_against_original_text():
    """Regression: canonical text is Latin-transliterated, so Cyrillic keywords
    must be matched against the original text too (previously dead logic)."""
    sanitized = TextSanitizer.sanitize("Куплю крипт и меф, доход гарантирован")
    score_result = RiskScorer.evaluate(
        sanitized=sanitized,
        user_message_count=100,
        user_days_in_chat=60,
        sampling_rate=0.0,
    )

    keyword_reasons = [r for r in score_result.trigger_reasons if r.startswith("keywords_matched")]
    assert keyword_reasons, "Cyrillic high-risk keywords must trigger AI inspection"
    assert score_result.should_call_ai is True


def test_boundary_keyword_does_not_fire_on_innocent_words():
    """'залив' must not match inside 'заливное' (word-boundary matching)."""
    sanitized = TextSanitizer.sanitize("Мама приготовила вкусное заливное на праздник")
    score_result = RiskScorer.evaluate(
        sanitized=sanitized,
        user_message_count=101,
        user_days_in_chat=60,
        sampling_rate=0.0,
    )

    keyword_reasons = [r for r in score_result.trigger_reasons if r.startswith("keywords_matched")]
    assert not keyword_reasons
    assert score_result.should_call_ai is False


def test_homoglyph_obfuscated_latin_keyword_still_matches():
    """Latin keywords must still match the transliterated canonical form."""
    sanitized = TextSanitizer.sanitize("сегодня огромный airdrop от крипто проекта")
    score_result = RiskScorer.evaluate(
        sanitized=sanitized,
        user_message_count=100,
        user_days_in_chat=60,
        sampling_rate=0.0,
    )

    keyword_reasons = [r for r in score_result.trigger_reasons if r.startswith("keywords_matched")]
    assert keyword_reasons
    assert score_result.should_call_ai is True


def test_separator_and_leet_obfuscated_keywords_match():
    """'З.а.р.а.б.о.т.ок' and 'airdr0p' must trigger keyword matching."""
    sanitized = TextSanitizer.sanitize("Секретный З.а.р.а.б.о.т.ок без вложений, честно")
    score_result = RiskScorer.evaluate(
        sanitized=sanitized,
        user_message_count=101,
        user_days_in_chat=60,
    )
    keyword_reasons = [r for r in score_result.trigger_reasons if r.startswith("keywords_matched")]
    assert keyword_reasons

    sanitized_leet = TextSanitizer.sanitize("сегодня огромный airdr0p от проекта")
    score_leet = RiskScorer.evaluate(
        sanitized=sanitized_leet,
        user_message_count=101,
        user_days_in_chat=60,
    )
    keyword_reasons = [r for r in score_leet.trigger_reasons if r.startswith("keywords_matched")]
    assert any("airdrop" in r for r in keyword_reasons)
