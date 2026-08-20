"""Pydantic schemas and enums for structured AI moderation verdicts."""

from enum import Enum
from pydantic import BaseModel, Field


class ViolationCategory(str, Enum):
    """Classification categories for moderated messages."""

    CLEAN = "clean"
    CRYPTO_SCAM = "crypto_scam"
    PHISHING = "phishing"
    COMMERCIAL_AD = "commercial_ad"
    ADULT_NSFW = "adult_nsfw"
    TOXIC_INSULT = "toxic_insult"
    FLOOD_SPAM = "flood_spam"
    OTHER_VIOLATION = "other_violation"


class SuggestedAction(str, Enum):
    """Enforced action suggested by the AI moderation engine."""

    PASS_MESSAGE = "pass_message"
    DELETE_MESSAGE = "delete_message"
    WARN = "warn"
    MUTE_USER = "mute_user"
    BAN_USER = "ban_user"


class AIModerationVerdict(BaseModel):
    """Strict structured response format from the AI Intent Engine."""

    is_violation: bool = Field(
        description="True if the message violates chat safety rules, spam policies, or is harmful."
    )
    category: ViolationCategory = Field(
        description="The primary classification category of the message."
    )
    confidence: float = Field(
        ge=0.0,
        le=100.0,
        description="Confidence score of the verdict from 0.0 to 100.0 percent.",
    )
    reason: str = Field(
        description="Concise human-readable explanation of why this verdict was reached in Russian."
    )
    suggested_action: SuggestedAction = Field(
        description="Recommended enforcement action based on severity."
    )
