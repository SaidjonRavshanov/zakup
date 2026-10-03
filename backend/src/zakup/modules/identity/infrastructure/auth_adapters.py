"""Autentifikatsiya port'lari implementatsiyasi: Telegram initData, JWT access, refresh token (DB)."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from zakup.modules.identity.application.dto import TelegramIdentity
from zakup.modules.identity.infrastructure.tables import refresh_tokens
from zakup.platform.access_tokens import AccessTokenCodec
from zakup.platform.telegram_auth import validate_init_data
from zakup.shared_kernel.auth import Principal
from zakup.shared_kernel.errors import UnauthenticatedError
from zakup.shared_kernel.ids import new_id


class InvalidRefreshTokenError(UnauthenticatedError):
    code = "invalid_refresh_token"


class TelegramInitDataVerifier:
    def __init__(self, bot_token: str, ttl_seconds: int) -> None:
        self._bot_token = bot_token
        self._ttl = ttl_seconds

    def verify(self, init_data: str) -> TelegramIdentity:
        user = validate_init_data(init_data, self._bot_token, self._ttl)
        return TelegramIdentity(
            telegram_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            language_code=user.language_code,
        )


class JwtAccessTokenIssuer:
    def __init__(self, codec: AccessTokenCodec) -> None:
        self._codec = codec

    def issue(self, principal: Principal) -> tuple[str, int]:
        return self._codec.issue(principal)


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


class SqlRefreshTokenStore:
    """Rotatsiya: har `consume` eski tokenni yopadi. Yopilgan token qayta kelsa — o'g'irlik belgisi,
    foydalanuvchining barcha sessiyalari yopiladi."""

    def __init__(self, session: AsyncSession, ttl_seconds: int) -> None:
        self._session = session
        self._ttl = timedelta(seconds=ttl_seconds)

    async def issue(self, user_id: UUID) -> str:
        raw = secrets.token_urlsafe(32)
        await self._session.execute(
            insert(refresh_tokens).values(
                id=new_id(), user_id=user_id, token_hash=_hash(raw), expires_at=datetime.now(UTC) + self._ttl
            )
        )
        return raw

    async def consume(self, raw_token: str) -> UUID:
        row = (
            await self._session.execute(
                select(
                    refresh_tokens.c.id,
                    refresh_tokens.c.user_id,
                    refresh_tokens.c.expires_at,
                    refresh_tokens.c.revoked_at,
                )
                .where(refresh_tokens.c.token_hash == _hash(raw_token))
                .with_for_update()
            )
        ).first()
        if row is None:
            raise InvalidRefreshTokenError("auth.refresh_invalid")
        if row.revoked_at is not None:
            await self.revoke_all(row.user_id)
            await self._session.commit()  # use case xato bilan tugaydi — bekor qilish saqlanib qolsin
            raise InvalidRefreshTokenError("auth.refresh_invalid")
        if row.expires_at <= datetime.now(UTC):
            raise InvalidRefreshTokenError("auth.refresh_expired")
        await self._session.execute(
            update(refresh_tokens).where(refresh_tokens.c.id == row.id).values(revoked_at=datetime.now(UTC))
        )
        user_id: UUID = row.user_id
        return user_id

    async def revoke(self, raw_token: str) -> None:
        await self._session.execute(
            update(refresh_tokens)
            .where(refresh_tokens.c.token_hash == _hash(raw_token), refresh_tokens.c.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )

    async def revoke_all(self, user_id: UUID) -> None:
        await self._session.execute(
            update(refresh_tokens)
            .where(refresh_tokens.c.user_id == user_id, refresh_tokens.c.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
