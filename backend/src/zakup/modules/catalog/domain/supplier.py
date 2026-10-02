"""Yetkazib beruvchi aggregate'i — sof Python, framework'siz (ARCHITECTURE §4)."""

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import ClassVar, Self
from uuid import UUID

from zakup.shared_kernel.errors import DomainError
from zakup.shared_kernel.events import AggregateRoot, DomainEvent
from zakup.shared_kernel.ids import new_id
from zakup.shared_kernel.money import Money

# O'zbekiston: yuridik shaxs STIR — 9 raqam, jismoniy shaxs JShShIR — 14 raqam
_INN_RE = re.compile(r"^(\d{9}|\d{14})$")
MAX_DEFERRAL_DAYS = 120


class PaymentTerms(StrEnum):
    PREPAY = "prepay"
    ON_DELIVERY = "on_delivery"
    DEFERRED = "deferred"


class InvalidSupplierError(DomainError):
    code = "invalid_supplier"


class DuplicateInnError(DomainError):
    code = "duplicate_inn"


@dataclass(frozen=True, kw_only=True)
class SupplierRegistered(DomainEvent):
    event_type: ClassVar[str] = "catalog.supplier_registered"
    name: str
    inn: str | None


@dataclass(frozen=True, kw_only=True)
class SupplierArchived(DomainEvent):
    event_type: ClassVar[str] = "catalog.supplier_archived"


class Supplier(AggregateRoot):
    aggregate_type: ClassVar[str] = "catalog.supplier"

    def __init__(
        self,
        *,
        id: UUID,  # noqa: A002 — domen atamasi
        name: str,
        inn: str | None,
        payment_terms: PaymentTerms,
        deferral_days: int,
        credit_limit: Money,
        min_order_amount: Money,
        iiko_id: UUID | None = None,
        archived_at: datetime | None = None,
        version: int = 1,
    ) -> None:
        super().__init__()
        self.id = id
        self.name = name
        self.inn = inn
        self.payment_terms = payment_terms
        self.deferral_days = deferral_days
        self.credit_limit = credit_limit
        self.min_order_amount = min_order_amount
        self.iiko_id = iiko_id
        self.archived_at = archived_at
        self.version = version

    @classmethod
    def register(
        cls,
        *,
        name: str,
        inn: str | None,
        payment_terms: PaymentTerms,
        deferral_days: int = 0,
        credit_limit: Money | None = None,
        min_order_amount: Money | None = None,
    ) -> Self:
        name = name.strip()
        inn = inn.strip() if inn else None
        _validate(name=name, inn=inn, payment_terms=payment_terms, deferral_days=deferral_days)
        supplier = cls(
            id=new_id(),
            name=name,
            inn=inn,
            payment_terms=payment_terms,
            deferral_days=deferral_days,
            credit_limit=credit_limit or Money.zero(),
            min_order_amount=min_order_amount or Money.zero(),
        )
        supplier.record(SupplierRegistered(aggregate_id=supplier.id, name=name, inn=inn))
        return supplier

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    def archive(self, at: datetime) -> None:
        """O'chirilmaydi — arxivlanadi: yangi zayavkalarda yo'q, tarixda qoladi (WORKFLOW B1)."""
        if self.is_archived:
            return
        self.archived_at = at
        self.record(SupplierArchived(aggregate_id=self.id))


def _validate(*, name: str, inn: str | None, payment_terms: PaymentTerms, deferral_days: int) -> None:
    if not name:
        raise InvalidSupplierError("supplier.name_empty")
    if inn is not None and not _INN_RE.match(inn):
        raise InvalidSupplierError("supplier.inn_format")
    if payment_terms is PaymentTerms.DEFERRED and not 0 < deferral_days <= MAX_DEFERRAL_DAYS:
        raise InvalidSupplierError("supplier.deferral_range", max=MAX_DEFERRAL_DAYS)
    if payment_terms is not PaymentTerms.DEFERRED and deferral_days != 0:
        raise InvalidSupplierError("supplier.deferral_only_deferred")
