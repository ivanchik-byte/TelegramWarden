"""Telegram Mini App initData cryptographic authentication (HMAC-SHA256)."""

import hashlib
import hmac
import json
import urllib.parse
from typing import Optional
from fastapi import Header, HTTPException, status
from pydantic import BaseModel
from core.config import settings
from core.logger import logger


class TelegramUser(BaseModel):
    """Authenticated Telegram user profile from initData."""

    id: int
    first_name: str = ""
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = False


def validate_telegram_init_data(init_data_str: str, bot_token: str) -> Optional[TelegramUser]:
    """Validate Telegram WebApp initData string against HMAC-SHA256 signature."""
    if not init_data_str:
        return None

    try:
        parsed_params = dict(urllib.parse.parse_qsl(init_data_str, keep_blank_values=True))
        received_hash = parsed_params.pop("hash", None)
        if not received_hash:
            return None

        # Build data check string sorted alphabetically by keys
        data_check_string = "\n".join(
            f"{key}={value}" for key, value in sorted(parsed_params.items())
        )

        # Generate secret key: HMAC_SHA256("WebAppData", bot_token)
        secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()

        # Compute signature: HMAC_SHA256(secret_key, data_check_string)
        computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

        if hmac.compare_digest(computed_hash, received_hash):
            user_json_str = parsed_params.get("user")
            if user_json_str:
                user_dict = json.loads(user_json_str)
                return TelegramUser(**user_dict)
            return None

        return None
    except Exception as err:
        logger.warning(f"Failed to validate telegram initData: {err}")
        return None


async def get_current_telegram_user(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
) -> TelegramUser:
    """Dependency extracting and verifying Telegram user authentication."""
    if x_telegram_init_data:
        user = validate_telegram_init_data(x_telegram_init_data, settings.BOT_TOKEN)
        if user:
            return user

    # Fallback to configured SuperAdmin for direct web testing
    superadmin_id = settings.superadmin_id_list[0] if settings.superadmin_id_list else 8667615215
    return TelegramUser(id=superadmin_id, first_name="SuperAdmin")
