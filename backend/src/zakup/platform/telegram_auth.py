"""Telegram Mini App `initData` tekshiruvi (ARCHITECTURE §7).

https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)
hash       = hex(HMAC_SHA256(key=secret_key, msg=data_check_string))
"""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl

from zakup.shared_kernel.errors import PermissionDeniedError


class InvalidInitDataError(PermissionDeniedError):
    code = "invalid_init_data"


@dataclass(frozen=True, slots=True)
class TelegramUser:
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None


def validate_init_data(init_data: str, bot_token: str, ttl_seconds: int, now: float | None = None) -> TelegramUser:
    if not init_data or not bot_token:
        raise InvalidInitDataError("auth.init_data_empty")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InvalidInitDataError("auth.init_data_no_hash")

    data_check_string = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash):
        raise InvalidInitDataError("auth.init_data_bad_signature")

    auth_date = int(pairs.get("auth_date", "0"))
    if (now or time.time()) - auth_date > ttl_seconds:
        raise InvalidInitDataError("auth.init_data_expired")

    try:
        user = json.loads(pairs["user"])
        return TelegramUser(
            id=int(user["id"]),
            first_name=str(user.get("first_name", "")),
            last_name=user.get("last_name"),
            username=user.get("username"),
            language_code=user.get("language_code"),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidInitDataError("auth.init_data_bad_user") from exc
