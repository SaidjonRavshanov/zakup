"""Yetkazib beruvchi aggregate'i — sof Python, framework'siz (ARCHITECTURE §4)."""

import re
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import StrEnum
from typing import ClassVar, Self
from uuid import UUID

from zakup.shared_kernel.errors import DomainError
from zakup.shared_kernel.events import AggregateRoot, DomainEvent
from zakup.shared_kernel.ids import new_id
from zakup.shared_kernel.money import Money

# O'zbekiston: yuridik shaxs STIR — 9 raqam, jismoniy shaxs JShShIR — 14 raqam
_INN_RE = re.compile(r"^(\d{9}|\d{14})$")
_PHONE_RE = re.compile(r"^\+?\d{9,15}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_DEFERRAL_DAYS = 120
MAX_LEAD_TIME_DAYS = 60
WEEKDAYS = frozenset(range(1, 8))  # ISO: 1 — dushanba, 7 — yakshanba


class PaymentTerms(StrEnum):
    PREPAY = "prepay"
    ON_DELIVERY = "on_delivery"
    DEFERRED = "deferred"


class InvalidSupplierError(DomainError):
    code = "invalid_supplier"


class DuplicateInnError(DomainError):
    code = "duplicate_inn"


@dataclass(frozen=True, slots=True)
class Contacts:
    """Buyurtma yuborish kanallari (WORKFLOW B6): Telegram / telefon / e-mail."""

    phone: str | None = None
    telegram: str | None = None
    email: str | None = None
    person: str | None = None

    def __post_init__(self) -> None:
        if self.phone and not _PHONE_RE.match(self.phone):
            raise InvalidSupplierError("supplier.phone_format")
        if self.email and not _EMAIL_RE.match(self.email):
            raise InvalidSupplierError("supplier.email_format")


@dataclass(frozen=True, slots=True)
class OrderSchedule:
    """Qaysi kunlari buyurtma qabul qiladi / yetkazadi, cut-off va yetkazish muddati (WORKFLOW B3, B6)."""

    lead_time_days: int = 1
    order_weekdays: frozenset[int] = field(default_factory=lambda: WEEKDAYS)
    delivery_weekdays: frozenset[int] = field(default_factory=lambda: WEEKDAYS)
    order_cutoff: time | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.lead_time_days <= MAX_LEAD_TIME_DAYS:
            raise InvalidSupplierError("supplier.lead_time_range", max=MAX_LEAD_TIME_DAYS)
        for days in (self.order_weekdays, self.delivery_weekdays):
            if not days or not days <= WEEKDAYS:
                raise InvalidSupplierError("supplier.weekdays")


@dataclass(frozen=True, kw_only=True)
class SupplierRegistered(DomainEvent):
    event_type: ClassVar[str] = "catalog.supplier_registered"
    name: str
    inn: str | None


@dataclass(frozen=True, kw_only=True)
class SupplierUpdated(DomainEvent):
    event_type: ClassVar[str] = "catalog.supplier_updated"


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
        schedule: OrderSchedule | None = None,
        contacts: Contacts | None = None,
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
        self.schedule = schedule or OrderSchedule()
        self.contacts = contacts or Contacts()
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
        schedule: OrderSchedule | None = None,
        contacts: Contacts | None = None,
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
            schedule=schedule,
            contacts=contacts,
        )
        supplier.record(SupplierRegistered(aggregate_id=supplier.id, name=name, inn=inn))
        return supplier

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    def revise(
        self,
        *,
        name: str,
        inn: str | None,
        payment_terms: PaymentTerms,
        deferral_days: int,
        credit_limit: Money,
        min_order_amount: Money,
        schedule: OrderSchedule,
        contacts: Contacts,
    ) -> None:
        """Rekvizitlar, to'lov sharti, jadval, kontaktlar — bitta forma bilan tahrirlanadi."""
        name = name.strip()
        inn = inn.strip() if inn else None
        _validate(name=name, inn=inn, payment_terms=payment_terms, deferral_days=deferral_days)
        self.name = name
        self.inn = inn
        self.payment_terms = payment_terms
        self.deferral_days = deferral_days
        self.credit_limit = credit_limit
        self.min_order_amount = min_order_amount
        self.schedule = schedule
        self.contacts = contacts
        self.record(SupplierUpdated(aggregate_id=self.id))

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
