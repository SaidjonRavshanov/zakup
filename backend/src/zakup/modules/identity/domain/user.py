"""Foydalanuvchi aggregate'i — sof Python (ARCHITECTURE §4, §7).

Ro'yxatdan o'tish: Telegram orqali birinchi kirishda foydalanuvchi **faol emas** holatda yaratiladi,
admin uni faollashtiradi va rol beradi. Begona Telegram akkaunt hech narsani ko'rmaydi.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Literal, Self
from uuid import UUID

from zakup.shared_kernel.auth import Principal, Role, RoleGrant
from zakup.shared_kernel.errors import DomainError, PermissionDeniedError
from zakup.shared_kernel.events import AggregateRoot, DomainEvent
from zakup.shared_kernel.ids import new_id

Locale = Literal["uz", "ru"]
DEFAULT_LOCALE: Locale = "uz"
MAX_GRANTS = 1000  # rol x ombor: 100+ ombor (Tarnov) — har biri alohida grant


def normalize_locale(language_code: str | None) -> Locale:
    base = (language_code or "").lower().split("-")[0]
    return "ru" if base == "ru" else DEFAULT_LOCALE


class AccountPendingError(PermissionDeniedError):
    """Akkaunt hali admin tomonidan faollashtirilmagan (yoki o'chirilgan)."""

    code = "account_pending"


class InvalidUserError(DomainError):
    code = "invalid_user"


class SelfLockoutError(DomainError):
    """Admin o'zini o'chira olmaydi / o'zidan admin rolini ola olmaydi — tizim adminsiz qolmasin."""

    code = "self_lockout"


@dataclass(frozen=True, kw_only=True)
class UserSignedUp(DomainEvent):
    event_type: ClassVar[str] = "identity.user_signed_up"
    telegram_id: int
    full_name: str


@dataclass(frozen=True, kw_only=True)
class UserActivated(DomainEvent):
    event_type: ClassVar[str] = "identity.user_activated"
    by: UUID | None


@dataclass(frozen=True, kw_only=True)
class UserDeactivated(DomainEvent):
    event_type: ClassVar[str] = "identity.user_deactivated"
    by: UUID


@dataclass(frozen=True, kw_only=True)
class UserRolesChanged(DomainEvent):
    event_type: ClassVar[str] = "identity.user_roles_changed"
    by: UUID
    grants: list[dict[str, str | None]]


class User(AggregateRoot):
    aggregate_type: ClassVar[str] = "identity.user"

    def __init__(
        self,
        *,
        id: UUID,  # noqa: A002 — domen atamasi
        telegram_id: int,
        full_name: str,
        username: str | None,
        locale: Locale,
        is_active: bool,
        grants: frozenset[RoleGrant] = frozenset(),
        activated_at: datetime | None = None,
        version: int = 1,
    ) -> None:
        super().__init__()
        self.id = id
        self.telegram_id = telegram_id
        self.full_name = full_name
        self.username = username
        self.locale = locale
        self.is_active = is_active
        self.grants = grants
        self.activated_at = activated_at
        self.version = version

    @classmethod
    def sign_up(cls, *, telegram_id: int, full_name: str, username: str | None, locale: Locale) -> Self:
        if telegram_id <= 0:
            raise InvalidUserError("user.telegram_id")
        user = cls(
            id=new_id(),
            telegram_id=telegram_id,
            full_name=_clean_name(full_name, telegram_id),
            username=username,
            locale=locale,
            is_active=False,
        )
        user.record(UserSignedUp(aggregate_id=user.id, telegram_id=telegram_id, full_name=user.full_name))
        return user

    def bootstrap_admin(self, at: datetime) -> None:
        """Konfiguratsiyadagi birinchi admin(lar): tizimni ishga tushirish uchun (ZAKUP_BOOTSTRAP_ADMIN_IDS)."""
        self.grants = self.grants | {RoleGrant(Role.ADMIN)}
        if not self.is_active:
            self.is_active = True
            self.activated_at = at
            self.record(UserActivated(aggregate_id=self.id, by=None))

    def refresh_profile(self, *, full_name: str, username: str | None) -> None:
        """Telegram'dagi ism / username o'zgargan bo'lishi mumkin — har kirishda yangilanadi."""
        self.full_name = _clean_name(full_name, self.telegram_id)
        self.username = username

    def change_locale(self, locale: Locale) -> None:
        self.locale = locale

    def ensure_can_sign_in(self) -> None:
        if not self.is_active:
            raise AccountPendingError("auth.account_pending")

    def activate(self, actor: Principal, at: datetime) -> None:
        if self.is_active:
            return
        self.is_active = True
        self.activated_at = at
        self.record(UserActivated(aggregate_id=self.id, by=actor.user_id))

    def deactivate(self, actor: Principal) -> None:
        if actor.user_id == self.id:
            raise SelfLockoutError("user.self_deactivate")
        if not self.is_active:
            return
        self.is_active = False
        self.record(UserDeactivated(aggregate_id=self.id, by=actor.user_id))

    def set_grants(self, grants: frozenset[RoleGrant], actor: Principal) -> None:
        if len(grants) > MAX_GRANTS:
            raise InvalidUserError("user.too_many_grants", max=MAX_GRANTS)
        # Admin — faqat barcha omborlarga (bitta omborli "admin" xodimlar va rollarni boshqara olmaydi)
        if any(g.role is Role.ADMIN and g.store_id is not None for g in grants):
            raise InvalidUserError("user.admin_must_be_global")
        if actor.user_id == self.id and not any(g.role is Role.ADMIN for g in grants):
            raise SelfLockoutError("user.self_remove_admin")
        if grants == self.grants:
            return
        self.grants = grants
        self.record(
            UserRolesChanged(
                aggregate_id=self.id,
                by=actor.user_id,
                grants=[
                    {"role": g.role.value, "store_id": str(g.store_id) if g.store_id else None}
                    for g in sorted(grants, key=lambda g: (g.role.value, str(g.store_id)))
                ],
            )
        )

    def principal(self) -> Principal:
        return Principal(user_id=self.id, grants=self.grants)


def _clean_name(full_name: str, telegram_id: int) -> str:
    name = " ".join(full_name.split())[:200]
    return name or f"tg:{telegram_id}"
