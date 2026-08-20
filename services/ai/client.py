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
        """Extract JSON block and parse into strict Pydantic model."""
        clean_json_str = raw_content.strip()

        # Check for markdown code fence
        match = JSON_BLOCK_PATTERN.search(clean_json_str)
        if match:
            clean_json_str = match.group(1).strip()

        parsed_dict = json.loads(clean_json_str)
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
