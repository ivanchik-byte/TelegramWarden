"""Unit tests for night mode window evaluation and sanction softening logic."""

from datetime import datetime
from unittest.mock import patch

from models import Chat
from services.moderation.night_mode import (
    get_night_mode_status,
    is_night_mode_active,
    _parse_hhmm,
)


def make_chat(**overrides) -> Chat:
    """Build a Chat model instance with night mode defaults and overrides."""
    chat = Chat(chat_id=-10042, title="Night Test")
    for key, value in {
        "night_mode_enabled": True,
        "night_mode_start": "23:00",
        "night_mode_end": "08:00",
        "night_mode_timezone": "UTC",
    }.items():
        setattr(chat, key, value)
    for key, value in overrides.items():
        setattr(chat, key, value)
    return chat


def test_parse_hhmm_valid_and_invalid():
    assert _parse_hhmm("23:00") == (23, 0)
    assert _parse_hhmm(" 8:05 ") == (8, 5)
    assert _parse_hhmm("24:00") is None
    assert _parse_hhmm("abc") is None
    assert _parse_hhmm("") is None


def test_disabled_night_mode_is_never_active():
    chat = make_chat(night_mode_enabled=False)
    status = get_night_mode_status(chat)
    assert status.is_active is False
    assert status.reason == "disabled"
    assert is_night_mode_active(chat) is False


def test_misconfigured_window_is_never_active():
    chat = make_chat(night_mode_start="25:99")
    status = get_night_mode_status(chat)
    assert status.is_active is False
    assert status.reason == "misconfigured"


def test_window_crossing_midnight_wraps_correctly():
    chat = make_chat()  # 23:00 -> 08:00

    with patch(
        "services.moderation.night_mode._now_in_chat_timezone",
        return_value=datetime(2026, 8, 25, 23, 30),
    ):
        assert is_night_mode_active(chat) is True

    with patch(
        "services.moderation.night_mode._now_in_chat_timezone",
        return_value=datetime(2026, 8, 26, 3, 0),
    ):
        assert is_night_mode_active(chat) is True

    # Boundary: end time itself is already day
    with patch(
        "services.moderation.night_mode._now_in_chat_timezone",
        return_value=datetime(2026, 8, 26, 8, 0),
    ):
        assert is_night_mode_active(chat) is False


def test_day_time_outside_window_is_not_night():
    chat = make_chat()
    with patch(
        "services.moderation.night_mode._now_in_chat_timezone",
        return_value=datetime(2026, 8, 25, 14, 0),
    ):
        assert is_night_mode_active(chat) is False


def test_same_day_window_without_wrap():
    chat = make_chat(night_mode_start="13:00", night_mode_end="15:00")

    with patch(
        "services.moderation.night_mode._now_in_chat_timezone",
        return_value=datetime(2026, 8, 25, 14, 0),
    ):
        assert is_night_mode_active(chat) is True

    with patch(
        "services.moderation.night_mode._now_in_chat_timezone",
        return_value=datetime(2026, 8, 25, 12, 59),
    ):
        assert is_night_mode_active(chat) is False


def test_unknown_timezone_falls_back_to_utc_semantics():
    chat = make_chat(night_mode_timezone="Mars/Olympus")

    with patch(
        "services.moderation.night_mode.datetime",
    ) as mock_dt:
        mock_dt.now.return_value = datetime(2026, 8, 25, 23, 30)
        mock_dt.side_effect = datetime
        status = get_night_mode_status(chat)
        assert status.is_active is True
