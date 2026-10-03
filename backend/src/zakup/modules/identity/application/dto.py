from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from zakup.modules.identity.domain.user import Locale
from zakup.shared_kernel.auth import RoleGrant

UserStatus = Literal["active", "pending"]


@dataclass(frozen=True, slots=True)
class TelegramIdentity:
    """Tekshirilgan (imzosi to'g'ri) Telegram foydalanuvchisi."""

    telegram_id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None

    @property
    def full_name(self) -> str:
        return " ".join(part for part in (self.first_name, self.last_name) if part)


@dataclass(frozen=True, slots=True)
class SessionTokens:
    access_token: str
    expires_in: int
    refresh_token: str


@dataclass(frozen=True, slots=True)
class UserProfile:
    id: UUID
    telegram_id: int
    full_name: str
    username: str | None
    locale: Locale
    is_active: bool
    grants: tuple[RoleGrant, ...]
