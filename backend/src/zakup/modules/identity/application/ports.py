"""Identity moduli port'lari — implementatsiyalar infrastructure qatlamida (DIP, ISP)."""

from typing import Protocol
from uuid import UUID

from zakup.modules.identity.application.dto import TelegramIdentity, UserProfile, UserStatus
from zakup.modules.identity.domain.user import User
from zakup.shared_kernel.auth import Principal


class UserRepository(Protocol):
    async def get(self, user_id: UUID) -> User | None: ...

    async def get_by_telegram_id(self, telegram_id: int) -> User | None: ...

    async def add(self, user: User) -> None: ...

    async def save(self, user: User) -> None:
        """Optimistic lock: version mos kelmasa ConflictError."""


class UserReader(Protocol):
    async def get(self, user_id: UUID) -> UserProfile | None: ...

    async def list(self, *, status: UserStatus | None, search: str | None, limit: int) -> list[UserProfile]: ...


class InitDataVerifier(Protocol):
    def verify(self, init_data: str) -> TelegramIdentity:
        """Imzo yoki muddat noto'g'ri bo'lsa — PermissionDeniedError."""


class AccessTokenIssuer(Protocol):
    def issue(self, principal: Principal) -> tuple[str, int]:
        """(token, amal qilish muddati soniyalarda)."""


class RefreshTokenStore(Protocol):
    async def issue(self, user_id: UUID) -> str: ...

    async def consume(self, raw_token: str) -> UUID:
        """Bir martalik: ishlatilgan token bekor qilinadi (rotatsiya). Yaroqsiz bo'lsa — UnauthenticatedError."""

    async def revoke(self, raw_token: str) -> None: ...

    async def revoke_all(self, user_id: UUID) -> None: ...
