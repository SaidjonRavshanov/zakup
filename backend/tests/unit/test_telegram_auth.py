import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from zakup.platform.telegram_auth import InvalidInitDataError, validate_init_data

BOT_TOKEN = "123456:TEST-TOKEN"


def make_init_data(auth_date: int, token: str = BOT_TOKEN, **extra: str) -> str:
    fields = {
        "auth_date": str(auth_date),
        "query_id": "AAH",
        "user": json.dumps({"id": 42, "first_name": "Aziz"}),
        **extra,
    }
    check = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


def test_valid_init_data() -> None:
    user = validate_init_data(make_init_data(int(time.time())), BOT_TOKEN, ttl_seconds=3600)
    assert user.id == 42
    assert user.first_name == "Aziz"


def test_wrong_token_rejected() -> None:
    with pytest.raises(InvalidInitDataError) as exc_info:
        validate_init_data(make_init_data(int(time.time()), token="999:OTHER"), BOT_TOKEN, ttl_seconds=3600)
    assert exc_info.value.key == "auth.init_data_bad_signature"


def test_tampered_field_rejected() -> None:
    data = make_init_data(int(time.time())).replace("Aziz", "Admin")
    with pytest.raises(InvalidInitDataError):
        validate_init_data(data, BOT_TOKEN, ttl_seconds=3600)


def test_expired_rejected() -> None:
    with pytest.raises(InvalidInitDataError) as exc_info:
        validate_init_data(make_init_data(int(time.time()) - 7200), BOT_TOKEN, ttl_seconds=3600)
    assert exc_info.value.key == "auth.init_data_expired"
