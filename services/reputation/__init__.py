"""Reputation and Global Spam Databases package."""

from services.reputation.cas import CASClient, CASCheckResult

__all__ = [
    "CASClient",
    "CASCheckResult",
]
