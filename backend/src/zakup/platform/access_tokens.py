"""Access token (JWT, HS256): qisqa muddatli, holatsiz — har so'rovda bazaga bormasdan `Principal` beradi.

Rollar token ichida: rol o'zgarsa, eski token ko'pi bilan `ttl` davomida amal qiladi (ARCHITECTURE §7: 15 daq).
"""

import time
from typing import Any
from uuid import UUID

import jwt

from zakup.shared_kernel.auth import Principal, Role, RoleGrant
from zakup.shared_kernel.errors import UnauthenticatedError

_ALGORITHM = "HS256"
_TYPE = "access"


class InvalidAccessTokenError(UnauthenticatedError):
    code = "invalid_token"


class AccessTokenCodec:
    def __init__(self, secret: str, ttl_seconds: int) -> None:
        if len(secret) < 32:  # noqa: PLR2004 — HS256 uchun kamida 256 bit
            raise RuntimeError("ZAKUP_JWT_SECRET kamida 32 belgidan iborat bo'lishi kerak")
        self._secret = secret
        self._ttl = ttl_seconds

    def issue(self, principal: Principal) -> tuple[str, int]:
        now = int(time.time())
        claims: dict[str, Any] = {
            "typ": _TYPE,
            "sub": str(principal.user_id),
            "iat": now,
            "exp": now + self._ttl,
            "grants": [[g.role.value, str(g.store_id) if g.store_id else None] for g in principal.grants],
        }
        return jwt.encode(claims, self._secret, algorithm=_ALGORITHM), self._ttl

    def decode(self, token: str) -> Principal:
        try:
            claims = jwt.decode(token, self._secret, algorithms=[_ALGORITHM], options={"require": ["exp", "sub"]})
        except jwt.ExpiredSignatureError as exc:
            raise InvalidAccessTokenError("auth.token_expired") from exc
        except jwt.InvalidTokenError as exc:
            raise InvalidAccessTokenError("auth.token_invalid") from exc
        if claims.get("typ") != _TYPE:
            raise InvalidAccessTokenError("auth.token_invalid")
        try:
            grants = frozenset(
                RoleGrant(Role(role), UUID(store_id) if store_id else None) for role, store_id in claims["grants"]
            )
            return Principal(user_id=UUID(claims["sub"]), grants=grants)
        except (KeyError, ValueError, TypeError) as exc:
            raise InvalidAccessTokenError("auth.token_invalid") from exc
