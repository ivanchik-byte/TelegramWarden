"""Heuristic risk-scoring engine to filter clean messages with 0 LLM tokens."""

import re
from typing import NamedTuple, Optional
from services.ai.normalizer import SanitizedTextResult

# High-risk trigger keywords for initial heuristic suspicion.
# Checked against the original text AND its Latin-transliterated canonical
# form, so Cyrillic keys survive homoglyph obfuscation.
HIGH_RISK_TRIGGER_KEYWORDS = [
    "крипт", "usdt", "ton", "доход", "заработ", "пассив", "в лс", "в личк",
    "сигнал", "трейдинг", "инвест", "airdrop", "дроп", "казино", "выплат",
    "ставки", "раздач", "бесплатно", "схема", "мануал", "onlyfans", "18+",
    "цп", "cp", "дп", "csam", "меф", "соли", "закладк", "альфа-пвп", "докс", "деанон", "сват",
    "залив", "кардинг", "дамп", "куки", "логи", "курьер",
    # collapsed alias: separator-stripped form of DM requests ("v.l.s." -> "vls")
    "влс", "вличку",
    "crypt", "invest", "profit", "earn", "income", "free usdt", "giveaway"
]

# Keywords matched with word boundaries regardless of length because their
# plain-substring form collides with innocent words (e.g. root substring collisions).
BOUNDARY_KEYWORDS = {"цп", "cp", "дп", "csam", "18+", "залив", "логи", "куки", "дамп", "дроп", "сват"}

# Deterministic inspection cadence bounds: every Nth message from an
# established user goes to the LLM no matter how clean it looks.
MIN_SAMPLING_CADENCE = 2
MAX_SAMPLING_CADENCE = 100

# Leetspeak and separator obfuscation (e.g. "airdr0p", "d.o.c.s")

_LEET_TRANSLATION = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s",
    "6": "b", "7": "t", "8": "b", "9": "g",
    "@": "a", "$": "s",
})
_TOKEN_SEPARATORS = re.compile(r"[^\wа-яё]+")


def _deobfuscate(text_lower: str) -> str:
    """Collapse leet digits and inner separators within each whitespace token."""
    return " ".join(
        _TOKEN_SEPARATORS.sub("", token.translate(_LEET_TRANSLATION))
        for token in text_lower.split()
    )


class RiskScoringResult(NamedTuple):
    """Result of heuristic risk evaluation."""

    should_call_ai: bool
    risk_score: int
    trigger_reasons: list[str]


class RiskScorer:
    """Evaluates message risk and decides whether LLM analysis is required."""

    @classmethod
    def cadence_from_rate(cls, sampling_rate: float) -> Optional[int]:
        """Convert a legacy sampling rate (0.0-1.0) into a message cadence.

        Zero or negative disables sampling entirely (None = never inspect
        clean traffic), it does not fall back to the default cadence.
        """
        if not sampling_rate or sampling_rate <= 0:
            return None
        return max(MIN_SAMPLING_CADENCE, min(MAX_SAMPLING_CADENCE, round(1 / sampling_rate)))

    @classmethod
    def evaluate(
        cls,
        sanitized: SanitizedTextResult,
        user_message_count: int = 100,
        user_days_in_chat: int = 30,
        is_forward: bool = False,
        sampling_rate: float = 0.05,
        telegram_id: int = 0,
    ) -> RiskScoringResult:
        """Calculate risk score and determine if AI inspection is needed."""
        cadence = cls.cadence_from_rate(sampling_rate)
        # Per-user phase derived from the stable Telegram ID: without jitter a
        # spammer could count messages and always strike right after the
        # inspected slot (9 clean, spam on the N-th).
        phase = telegram_id % cadence if cadence else 0
        risk_score = 0
        trigger_reasons: list[str] = []

        # Accounts under 3 days or with fewer than 5 messages are weighted heavily
        is_newcomer = (user_days_in_chat < 3) or (user_message_count < 5)
        if is_newcomer:
            risk_score += 30
            trigger_reasons.append("newcomer_activity")

        # Forwarded content is frequently used in spam syndicates to bypass sender attribution
        if is_forward:
            risk_score += 35
            trigger_reasons.append("forwarded_message")

        # External URLs are primary scam vectors
        if sanitized.extracted_urls:
            risk_score += 45
            trigger_reasons.append(f"contains_urls:{len(sanitized.extracted_urls)}")

        # Mentions and bot handles often funnel victims into private chats
        if sanitized.extracted_usernames:
            risk_score += 25
            trigger_reasons.append(f"contains_mentions:{len(sanitized.extracted_usernames)}")

        # Invisible Zero-Width and RTL marks strongly indicate deliberate evasion
        if sanitized.had_invisible_characters:
            risk_score += 50
            trigger_reasons.append("invisible_characters_detected")

        # Match keywords against four text variants: original, Latin-canonical,
        # and both de-obfuscated forms (leet digits and dotted spelling).
        variants = [
            sanitized.clean_text.lower(),
            sanitized.canonical_text.lower(),
        ]
        variants.extend(_deobfuscate(v) for v in list(variants))

        def _matches(kw: str, haystack: str) -> bool:
            if kw in BOUNDARY_KEYWORDS or len(kw) <= 3:
                pattern = r'(?:^|\s|[^\w\d])' + re.escape(kw) + r'(?:$|\s|[^\w\d])'
                return bool(re.search(pattern, haystack))
            return kw in haystack

        matched_keywords: list[str] = []
        for kw in HIGH_RISK_TRIGGER_KEYWORDS:
            if any(_matches(kw, variant) for variant in variants):
                matched_keywords.append(kw)

        if matched_keywords:
            risk_score += 40
            unique_matched = sorted(set(matched_keywords))
            trigger_reasons.append(f"keywords_matched:{','.join(unique_matched[:3])}")

        # Established users with zero accumulated risk bypass LLM calls, except for
        # deterministic cadence checks with per-user jitter to catch sleeper bots.
        if risk_score == 0 and not is_newcomer:
            if cadence and user_message_count > 0 and user_message_count % cadence == phase:
                return RiskScoringResult(
                    should_call_ai=True,
                    risk_score=10,
                    trigger_reasons=["scheduled_sampling_check"],
                )
            return RiskScoringResult(
                should_call_ai=False,
                risk_score=0,
                trigger_reasons=[],
            )

        # Any significant accumulated risk triggers AI. (is_newcomer is not
        # checked here: it already contributes +30 to the score.)
        should_call_ai = risk_score >= 25

        return RiskScoringResult(
            should_call_ai=should_call_ai,
            risk_score=risk_score,
            trigger_reasons=trigger_reasons,
        )
