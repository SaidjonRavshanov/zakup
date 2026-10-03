import time

import jwt
import pytest

from zakup.platform.access_tokens import AccessTokenCodec, InvalidAccessTokenError
from zakup.shared_kernel.auth import Principal, Role, RoleGrant
from zakup.shared_kernel.ids import new_id

SECRET = "x" * 40


def test_roundtrip_keeps_grants() -> None:
    codec = AccessTokenCodec(SECRET, ttl_seconds=60)
    principal = Principal(
        user_id=new_id(), grants=frozenset({RoleGrant(Role.BUYER), RoleGrant(Role.STOREKEEPER, new_id())})
    )
    token, expires_in = codec.issue(principal)
    assert expires_in == 60
    assert codec.decode(token) == principal


def test_wrong_secret_is_rejected() -> None:
    token, _ = AccessTokenCodec(SECRET, 60).issue(Principal(user_id=new_id(), grants=frozenset()))
    with pytest.raises(InvalidAccessTokenError) as exc:
        AccessTokenCodec("y" * 40, 60).decode(token)
    assert exc.value.key == "auth.token_invalid"


def test_expired_token_is_rejected() -> None:
    now = int(time.time())
    token = jwt.encode({"typ": "access", "sub": str(new_id()), "exp": now - 1, "grants": []}, SECRET, "HS256")
    with pytest.raises(InvalidAccessTokenError) as exc:
        AccessTokenCodec(SECRET, 60).decode(token)
    assert exc.value.key == "auth.token_expired"


def test_unknown_role_is_rejected() -> None:
    claims = {"typ": "access", "sub": str(new_id()), "exp": int(time.time()) + 60, "grants": [["root", None]]}
    with pytest.raises(InvalidAccessTokenError):
        AccessTokenCodec(SECRET, 60).decode(jwt.encode(claims, SECRET, "HS256"))


def test_short_secret_is_refused() -> None:
    with pytest.raises(RuntimeError):
        AccessTokenCodec("short", 60)
