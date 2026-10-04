"""Kim so'rov yuboryapti va unga nima mumkin — barcha modullar uchun umumiy (ARCHITECTURE §7).

Ruxsat application qatlamida tekshiriladi (router'da emas): use case `Principal` oladi
va `actor.require(Role.BUYER, Role.ADMIN)` chaqiradi.
"""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from zakup.shared_kernel.errors import PermissionDeniedError

# Avtomatik hujjatlar muallifi (avto-zayavka): identity.users'da faol bo'lmagan yozuv (migratsiya 0008)
SYSTEM_USER_ID = UUID("00000000-0000-7000-8000-000000000001")


class Role(StrEnum):
    INITIATOR = "initiator"
    BUYER = "buyer"
    APPROVER = "approver"
    STOREKEEPER = "storekeeper"
    ACCOUNTANT = "accountant"
    AUDITOR = "auditor"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class RoleGrant:
    """Rol + ombor doirasi. `store_id=None` — barcha omborlarda."""

    role: Role
    store_id: UUID | None = None

    def covers(self, store_id: UUID | None) -> bool:
        return self.store_id is None or store_id is None or self.store_id == store_id


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: UUID
    grants: frozenset[RoleGrant]

    def has_role(self, *roles: Role, store_id: UUID | None = None) -> bool:
        """`store_id=None` — "qaysidir omborda shu rol bormi"."""
        return any(grant.role in roles and grant.covers(store_id) for grant in self.grants)

    def require(self, *roles: Role, store_id: UUID | None = None) -> None:
        if not self.has_role(*roles, store_id=store_id):
            raise PermissionDeniedError("auth.role_required")

    @property
    def roles(self) -> frozenset[Role]:
        return frozenset(grant.role for grant in self.grants)
