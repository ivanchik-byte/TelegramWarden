"""Asynchronous AI Intent Engine with multi-provider fallback and JSON validation."""

import json
import re
from typing import Optional
import httpx
from openai import AsyncOpenAI

from core.config import settings
from core.logger import logger
from services.ai.prompts import SYSTEM_MODERATION_PROMPT
from services.ai.schema import (
    AIModerationVerdict,
    SuggestedAction,
    ViolationCategory,
)

JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

# Per-category confidence bands (floor, ceiling). Ceilings for warn/mute-tier
# categories stay below the default ban threshold (85%) so that raw LLM
# overconfidence alone can never trigger a confidence-based ban.
CATEGORY_CONFIDENCE_BANDS = {
    "toxic_insult": (5.0, 84.0),
    "commercial_ad": (5.0, 84.0),
    "flood_spam": (5.0, 94.0),
    "other_violation": (5.0, 94.0),
    "crypto_scam": (50.0, 99.0),
    "phishing": (50.0, 99.0),
    # Low floor: an unsure LLM must not be clamped UP into the ban tier.
    # Severe-contraband banning is driven by the category flag, not confidence.
    "illegal_contraband": (10.0, 99.0),
    "adult_nsfw": (60.0, 99.0),
}


class AIClientDispatcher:
    """Dispatches moderation queries to Primary (DeepSeek) or Fallback (Groq/OpenAI) LLM."""

    def __init__(self) -> None:
        # Primary client (DeepSeek)
        self.primary_client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=httpx.Timeout(10.0, connect=3.0),
        )

        # Fallback client (Groq / OpenRouter / OpenAI)
        self.fallback_client: Optional[AsyncOpenAI] = None
        if settings.FALLBACK_AI_ENABLED and settings.FALLBACK_API_KEY:
            self.fallback_client = AsyncOpenAI(
                api_key=settings.FALLBACK_API_KEY,
                base_url=settings.FALLBACK_BASE_URL,
                timeout=httpx.Timeout(8.0, connect=2.0),
            )

    @classmethod
    def _extract_and_parse_json(cls, raw_content: str) -> AIModerationVerdict:
        """Extract JSON block and parse into strict Pydantic model with calibrated threat risk."""
        clean_json_str = raw_content.strip()

        # Check for markdown code fence
        match = JSON_BLOCK_PATTERN.search(clean_json_str)
        if match:
            clean_json_str = match.group(1).strip()

        parsed_dict = json.loads(clean_json_str)

        # Normalize LLM output fields: an unknown category/action must degrade
        # gracefully instead of failing validation and discarding the verdict.
        is_violation = bool(parsed_dict.get("is_violation", False))
        category_key = str(parsed_dict.get("category", "clean")).lower().strip()
        if category_key not in {c.value for c in ViolationCategory}:
            # A hallucinated category still counts as a flagged violation.
            category_key = "other_violation" if is_violation else "clean"
            parsed_dict["category"] = category_key

        action_key = str(parsed_dict.get("suggested_action", "pass_message")).lower().strip()
        if action_key not in {a.value for a in SuggestedAction}:
            action_key = "pass_message" if category_key == "clean" else "warn"
            parsed_dict["suggested_action"] = action_key

        try:
            conf = float(parsed_dict.get("confidence", 0.0))
        except (TypeError, ValueError):
            conf = 0.0

        # Normalize Confidence to Threat Risk (0% = Safe Green, 100% = Danger Red)
        if not is_violation or category_key == "clean":
            # Threat risk of a clean message is always low; clamp instead of
            # inverting so the scale stays monotonic and predictable.
            parsed_dict["is_violation"] = False
            parsed_dict["category"] = "clean"
            parsed_dict["confidence"] = min(max(conf, 1.0), 15.0)
            parsed_dict["suggested_action"] = "pass_message"
        else:
            # Clamp violation confidence into its category band: preserves the
            # model's relative certainty while preventing habitual extremes (1%/99%).
            floor, ceiling = CATEGORY_CONFIDENCE_BANDS.get(category_key, (5.0, 94.0))
            parsed_dict["confidence"] = round(min(max(conf, floor), ceiling), 1)

        return AIModerationVerdict.model_validate(parsed_dict)

    async def analyze_message(
        self,
        message_text: str,
        user_info: Optional[str] = None,
        chat_context: Optional[list[str]] = None,
    ) -> AIModerationVerdict:
        """Analyze message intent and return structured moderation verdict."""
        # Construct user prompt with optional context
        prompt_parts = []
        if user_info:
            prompt_parts.append(f"User context: {user_info}")
        if chat_context:
            prompt_parts.append("Recent chat messages:\n" + "\n".join(chat_context[-3:]))
        prompt_parts.append(f"Target message to inspect:\n\"{message_text}\"")
        user_content = "\n\n".join(prompt_parts)

        messages = [
            {"role": "system", "content": SYSTEM_MODERATION_PROMPT},
            {"role": "user", "content": user_content},
        ]

        # 1. Try Primary LLM Provider (DeepSeek)
        try:
            response = await self.primary_client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=400,
            )
            raw_text = response.choices[0].message.content or "{}"
            return self._extract_and_parse_json(raw_text)

        except Exception as primary_err:
            logger.warning(f"Primary AI Provider failed: {primary_err}")

            # 2. Try Fallback Provider if available
            if self.fallback_client:
                try:
                    logger.info("Switching to Fallback AI Provider...")
                    fallback_response = await self.fallback_client.chat.completions.create(
                        model=settings.FALLBACK_MODEL,
                        messages=messages,
                        response_format={"type": "json_object"},
                        temperature=0.1,
                        max_tokens=400,
                    )
                    raw_text = fallback_response.choices[0].message.content or "{}"
                    return self._extract_and_parse_json(raw_text)
                except Exception as fallback_err:
                    logger.error(f"Fallback AI Provider also failed: {fallback_err}")

        # 3. Safe Default Verdict in case of total provider failure
        return AIModerationVerdict(
            is_violation=False,
            category=ViolationCategory.CLEAN,
            confidence=0.0,
            reason="AI Provider unavailable (fail-open to prevent false bans)",
            suggested_action=SuggestedAction.PASS_MESSAGE,
        )


# Global AI client singleton
ai_dispatcher = AIClientDispatcher()
