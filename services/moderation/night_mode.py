"""Night mode enforcement: soften sanctions during admin-configured quiet hours.

During the night window violations are still deleted and logged for admin
review, but punitive sanctions (warn/mute/ban) are deferred so that sleepy
false positives do not punish members while admins are away.
"""

from datetime import datetime, timezone
from typing import NamedTuple, Optional

from models import Chat

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9 fallback
    ZoneInfo = None


class NightModeStatus(NamedTuple):
    """Result of night mode evaluation."""

    is_active: bool
    reason: str


def _parse_hhmm(value: str) -> Optional[tuple[int, int]]:
    """Parse an 'HH:MM' string into (hour, minute), or None when malformed."""
    try:
        parts = value.strip().split(":")
        if len(parts) != 2:
            return None
        hour, minute = int(parts[0]), int(parts[1])
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute
    except (ValueError, AttributeError, IndexError):
        pass
    return None


def _now_in_chat_timezone(tz_name: str) -> datetime:
    """Current time in the chat's configured timezone (UTC on bad names)."""
    if ZoneInfo and tz_name:
        try:
            return datetime.now(ZoneInfo(tz_name))
        except Exception:
            pass
    return datetime.now(timezone.utc)


def get_night_mode_status(chat_db: Chat) -> NightModeStatus:
    """Evaluate whether the chat is currently inside its night mode window."""
    if not getattr(chat_db, "night_mode_enabled", False):
        return NightModeStatus(is_active=False, reason="disabled")

    start = _parse_hhmm(getattr(chat_db, "night_mode_start", "") or "")
    end = _parse_hhmm(getattr(chat_db, "night_mode_end", "") or "")
    if start is None or end is None:
        return NightModeStatus(is_active=False, reason="misconfigured")

    now_local = _now_in_chat_timezone(getattr(chat_db, "night_mode_timezone", "") or "UTC")
    current = now_local.hour * 60 + now_local.minute
    start_min = start[0] * 60 + start[1]
    end_min = end[0] * 60 + end[1]

    # Window crossing midnight (e.g. 23:00 -> 08:00) wraps around zero
    if start_min <= end_min:
        is_night = start_min <= current < end_min
    else:
        is_night = current >= start_min or current < end_min

    return NightModeStatus(
        is_active=is_night,
        reason="night_window" if is_night else "day_window",
    )


def is_night_mode_active(chat_db: Chat) -> bool:
    """Boolean shortcut for sanction-softening checks in moderation handlers."""
    return get_night_mode_status(chat_db).is_active
