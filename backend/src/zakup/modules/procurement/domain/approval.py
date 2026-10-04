"""Tasdiqlash matritsasi va rollar ajratilishi (WORKFLOW B5, 2-bo'lim).

Limitlar — sozlamada (ZAKUP_APPROVAL_LIMITS); javoblar kelguncha default: zakupshik 2 mln, boshqaruvchi 10 mln,
admin — cheklanmagan. Tasdiqlovchi = tashabbuskor bo'lsa ham ruxsat, lekin `role_conflict` belgilanadi.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from zakup.shared_kernel.auth import Principal, Role
from zakup.shared_kernel.errors import PermissionDeniedError

APPROVER_ROLES = (Role.BUYER, Role.APPROVER, Role.ADMIN)


class ApprovalLimitError(PermissionDeniedError):
    code = "approval_limit"


class Decision(StrEnum):
    APPROVED = "approved"
    PARTIAL = "partial"
    RETURNED = "returned"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class ApprovalPolicy:
    """Rol → maksimal summa (None — cheklanmagan). Rol ombor doirasida bo'lishi kerak."""

    limits: dict[Role, Decimal | None] = field(
        default_factory=lambda: {Role.BUYER: Decimal(2_000_000), Role.APPROVER: Decimal(10_000_000), Role.ADMIN: None}
    )

    def limit_for(self, actor: Principal, store_id: UUID) -> Decimal | None:
        """Aktorning shu ombordagi eng katta limiti; rol yo'q bo'lsa — Decimal(-1) (hech narsa tasdiqlay olmaydi)."""
        best = Decimal(-1)
        for role, limit in self.limits.items():
            if not actor.has_role(role, store_id=store_id):
                continue
            if limit is None:
                return None
            best = max(best, limit)
        return best

    def ensure_can_approve(self, actor: Principal, store_id: UUID, amount: Decimal) -> None:
        limit = self.limit_for(actor, store_id)
        if limit is not None and amount > limit:
            if limit < 0:
                raise ApprovalLimitError("approval.no_role")
            raise ApprovalLimitError("approval.over_limit", limit=limit, amount=amount)


@dataclass(frozen=True, slots=True)
class ApprovalRecord:
    """Har bir qaror (WORKFLOW B5: "Всё пишется в аудит-лог")."""

    approver_id: UUID
    decision: Decision
    comment: str | None
    amount: Decimal
    role_conflict: bool
    decided_at: datetime
