"""Tier-1 fast triage via TypeSafe Jev (System One decision model).

Jev answers typed questions about a message and returns calibrated
probabilities without generating text. Any failure (timeout, 429/529,
network) yields None so the dispatcher falls through to the LLM tier.
A 401 disables the tier via circuit breaker: retrying a dead key on every
message would stall the moderation queue.
"""

import asyncio
import time
from typing import NamedTuple, Optional

import httpx

from core.logger import logger
from services.ai.schema import ViolationCategory

SYSTEMONE_PATH = "/v1/systemone"

CATEGORY_DESCRIPTIONS = {
    "clean": "ordinary conversation, no spam, scam, abuse or harmful content",
    "crypto_scam": "fake giveaways, airdrops, investment or doubling schemes",
    "phishing": "fake logins, stolen credentials, impersonation of services",
    "commercial_ad": "unsolicited ads, channel promos, referral links",
    "adult_nsfw": "sexual content, explicit imagery offers",
    "toxic_insult": "insults, harassment, hate toward members",
    "flood_spam": "mass reposts, copy-paste raids, gibberish flooding",
    "illegal_contraband": "drugs, weapons, carding, doxxing, CSAM",
    "other_violation": "harmful content not covered by the other categories",
}

# A nonzero mass on these always escalates to the LLM tier, even under the
# fast-pass threshold: missing one costs more than any saved LLM call.
CRITICAL_CATEGORIES = frozenset({"illegal_contraband", "phishing"})


class JevTriageResult(NamedTuple):
    """Calibrated triage outcome for one message."""

    is_violation_prob: float
    top_category: str
    category_probabilities: dict[str, float]
    latency_ms: float


class JevClient:
    """Minimal async client for the TypeSafe System One API."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float = 2.5,
        max_concurrent: int = 10,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self._model = model
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=httpx.Timeout(timeout_seconds, connect=min(3.0, timeout_seconds)),
            limits=httpx.Limits(max_keepalive_connections=max_concurrent),
            transport=transport,
        )
        self._disabled = False
        self._frozen_until = 0.0
        self._key_warned = False

    async def triage(self, text: str) -> Optional[JevTriageResult]:
        """Classify one message; None means 'fall through to the LLM tier'."""
        if self._disabled or not text.strip():
            return None
        if time.monotonic() < self._frozen_until:
            return None

        payload = {
            "model": self._model,
            "state": {"messages": {"m0": {"text": text}}},
            "questions": {
                "is_violation": {
                    "type": "noul",
                    "instructions": "Does this message violate chat rules (spam, scam, phishing, ads, abuse, harmful content)?",
                    "criteria": {
                        "true": "spam, scam, phishing, unsolicited ads, insults or harmful content",
                        "false": "ordinary harmless conversation",
                    },
                },
                "category": {
                    "type": "choice",
                    "instructions": "Which moderation category fits this message best?",
                    "criteria": CATEGORY_DESCRIPTIONS,
                },
            },
        }

        started = time.monotonic()
        try:
            async with self._semaphore:
                response = await self._http.post(SYSTEMONE_PATH, json=payload)
        except Exception as err:
            logger.debug(f"Jev triage unreachable: {err}")
            return None
        latency_ms = (time.monotonic() - started) * 1000.0

        if response.status_code == 401:
            if not self._key_warned:
                self._key_warned = True
                logger.critical("Jev API key invalid, disabling Jev tier")
            self._disabled = True
            return None
        if response.status_code == 429:
            retry_after = float(response.headers.get("Retry-After", "30"))
            self._frozen_until = time.monotonic() + min(max(retry_after, 1.0), 300.0)
            logger.warning(f"Jev rate-limited, freezing tier for {retry_after:.0f}s")
            return None
        if response.status_code != 200:
            logger.debug(f"Jev triage HTTP {response.status_code}, falling through")
            return None

        try:
            return self._parse(response.json(), latency_ms)
        except Exception as err:
            logger.debug(f"Jev triage unparsable: {err}")
            return None

    @staticmethod
    def _parse(body: dict, latency_ms: float) -> Optional[JevTriageResult]:
        answers = body.get("answers", {})
        noul = answers.get("is_violation", {}).get("noul")
        choice = answers.get("category", {})
        if not isinstance(noul, (int, float)) or not 0.0 <= noul <= 1.0:
            return None
        top = choice.get("choice")
        probs = choice.get("probabilities", {})
        if top not in CATEGORY_DESCRIPTIONS or not isinstance(probs, dict):
            top = "other_violation"
            probs = {}
        if top not in {c.value for c in ViolationCategory}:
            top = "other_violation"
        return JevTriageResult(
            is_violation_prob=float(noul),
            top_category=top,
            category_probabilities={k: float(v) for k, v in probs.items()},
            latency_ms=latency_ms,
        )

    async def aclose(self) -> None:
        await self._http.aclose()
