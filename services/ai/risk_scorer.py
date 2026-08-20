"""Heuristic risk-scoring engine to filter clean messages with 0 LLM tokens."""

import random
from typing import NamedTuple, Optional
from services.ai.normalizer import SanitizedTextResult

# High-risk trigger keywords for initial heuristic suspicion
HIGH_RISK_TRIGGER_KEYWORDS = [
    "крипт", "usdt", "ton", "доход", "заработ", "пассив", "в лс", "в личк",
    "сигнал", "трейдинг", "инвест", "airdrop", "дроп", "казино", "выплат",
    "ставки", "раздач", "бесплатно", "схема", "мануал", "onlyfans", "18+",
    "crypt", "invest", "profit", "earn", "income", "free usdt", "giveaway"
]


class RiskScoringResult(NamedTuple):
    """Result of heuristic risk evaluation."""

    should_call_ai: bool
    risk_score: int
    trigger_reasons: list[str]


class RiskScorer:
    """Evaluates message risk and decides whether LLM analysis is required."""

    @classmethod
    def evaluate(
        cls,
        sanitized: SanitizedTextResult,
        user_message_count: int = 100,
        user_days_in_chat: int = 30,
        is_forward: bool = False,
        sampling_rate: float = 0.05,
    ) -> RiskScoringResult:
        """Calculate risk score and determine if AI inspection is needed."""
        risk_score = 0
        trigger_reasons: list[str] = []

        # 1. Newcomer penalty (< 3 days or < 5 messages)
        is_newcomer = (user_days_in_chat < 3) or (user_message_count < 5)
        if is_newcomer:
            risk_score += 30
            trigger_reasons.append("newcomer_activity")

        # 2. Forwarded message from another channel/chat
        if is_forward:
            risk_score += 35
            trigger_reasons.append("forwarded_message")

        # 3. External URLs detected
        if sanitized.extracted_urls:
            risk_score += 45
            trigger_reasons.append(f"contains_urls:{len(sanitized.extracted_urls)}")

        # 4. @usernames or bot links detected
        if sanitized.extracted_usernames:
            risk_score += 25
            trigger_reasons.append(f"contains_mentions:{len(sanitized.extracted_usernames)}")

        # 5. Invisible Zero-Width / RTL bypass characters
        if sanitized.had_invisible_characters:
            risk_score += 50
            trigger_reasons.append("invisible_characters_detected")

        # 6. High-risk keywords in canonical text
        lowered_canonical = sanitized.canonical_text.lower()
        matched_keywords = [kw for kw in HIGH_RISK_TRIGGER_KEYWORDS if kw in lowered_canonical]
        if matched_keywords:
            risk_score += 40
            trigger_reasons.append(f"keywords_matched:{','.join(matched_keywords[:3])}")

        # 7. Short clean messages from established users bypass with 0 tokens
        if risk_score == 0 and not is_newcomer and len(sanitized.clean_text) < 150:
            # Periodic random sampling (e.g. 5%) to catch rogue/compromised old accounts
            if random.random() < sampling_rate:
                return RiskScoringResult(
                    should_call_ai=True,
                    risk_score=10,
                    trigger_reasons=["random_sampling_check"],
                )
            return RiskScoringResult(
                should_call_ai=False,
                risk_score=0,
                trigger_reasons=[],
            )

        # If any significant risk is accumulated, trigger AI
        should_call_ai = risk_score >= 25 or is_newcomer

        return RiskScoringResult(
            should_call_ai=should_call_ai,
            risk_score=risk_score,
            trigger_reasons=trigger_reasons,
        )
