"""integration_iiko port'lari. iiko bilan faqat shu modul gaplashadi (ADR-05)."""

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID

from zakup.modules.integration_iiko.domain.mapping import PaymentMethod
from zakup.modules.integration_iiko.domain.models import (
    IikoDepartment,
    IikoIncomingInvoice,
    IikoProduct,
    IikoProductGroup,
    IikoStore,
    IikoSupplier,
    IikoUnit,
)


class IikoReader(Protocol):
    """Ochiq sessiya ichidagi o'qish metodlari (faqat GET)."""

    async def departments(self) -> list[IikoDepartment]: ...

    async def stores(self) -> list[IikoStore]: ...

    async def units(self) -> list[IikoUnit]: ...

    async def product_groups(self) -> list[IikoProductGroup]: ...

    async def products(self) -> list[IikoProduct]: ...

    async def suppliers(self) -> list[IikoSupplier]: ...

    async def incoming_invoices(self, date_from: date, date_to: date) -> list[IikoIncomingInvoice]: ...


@dataclass(frozen=True, slots=True)
class ServerInfo:
    code: str
    name: str
    department_code: str | None


class IikoGateway(Protocol):
    def servers(self) -> list[ServerInfo]: ...

    def session(self, server_code: str) -> AbstractAsyncContextManager[IikoReader]:
        """auth → (blok: bitta sessiya serverga) → ... → logout (har doim)."""


class EntityKind(StrEnum):
    BRANCH = "branch"
    STORE = "store"
    CATEGORY = "category"
    PRODUCT = "product"
    SUPPLIER = "supplier"


class Links(Protocol):
    """iiko GUID ↔ bizning ID. Bir xil tovar/yetkazuvchi har serverda boshqa GUID bilan bo'lishi mumkin."""

    async def local_id(self, server: str, kind: EntityKind, iiko_id: UUID) -> UUID | None: ...

    async def local_id_any_server(self, kind: EntityKind, iiko_id: UUID) -> UUID | None: ...

    async def local_id_by_key(self, kind: EntityKind, key: str) -> UUID | None:
        """Tabiiy kalit bo'yicha (yetkazuvchi: normallashtirilgan nom)."""

    async def save(
        self,
        server: str,
        kind: EntityKind,
        iiko_id: UUID,
        local_id: UUID,
        *,
        key: str | None = None,
        attrs: dict[str, Any] | None = None,
    ) -> None: ...


class CatalogSync(Protocol):
    """catalog modulining public interfeysi.

    ARCHITECTURE §3.1: boshqa modul jadvaliga to'g'ridan-to'g'ri yozilmaydi.
    """

    async def upsert_branch(self, local_id: UUID | None, *, iiko_id: UUID, code: str | None, name: str) -> UUID: ...

    async def upsert_store(
        self, local_id: UUID | None, *, iiko_id: UUID, name: str, branch_id: UUID | None
    ) -> UUID: ...

    async def upsert_category(
        self, local_id: UUID | None, *, iiko_id: UUID, name: str, parent_id: UUID | None
    ) -> UUID: ...

    async def find_product_by_article(self, article: str) -> UUID | None: ...

    async def upsert_product(
        self,
        local_id: UUID | None,
        *,
        iiko_id: UUID,
        name: str,
        article: str | None,
        base_unit: str,
        category_id: UUID | None,
        archived: bool,
    ) -> UUID: ...

    async def upsert_supplier(
        self,
        local_id: UUID | None,
        *,
        iiko_id: UUID,
        name: str,
        phone: str | None,
        inn: str | None,
        payment_method: PaymentMethod | None,
    ) -> UUID: ...

    async def record_purchase_price(
        self, *, supplier_id: UUID, product_id: UUID, price_per_base_unit: Decimal, on: date
    ) -> bool:
        """Nakladnoydagi narx → taklif (1 bazaviy birlik) + narx tarixi (source=iiko). True — yangi narx yozildi."""


class SyncKind(StrEnum):
    REFERENCES = "references"  # bo'limlar, omborlar, guruhlar, tovarlar, yetkazuvchilar
    PURCHASE_PRICES = "purchase_prices"  # nakladnoylardan oxirgi xarid narxlari


class SyncStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class SyncRun:
    id: UUID
    server_code: str
    kind: SyncKind
    status: SyncStatus
    params: dict[str, Any]


class SyncRuns(Protocol):
    async def enqueue(
        self, *, server_code: str, kind: SyncKind, params: dict[str, Any], requested_by: UUID | None
    ) -> UUID: ...

    async def has_pending(self, server_code: str, kind: SyncKind) -> bool: ...

    async def claim_next(self) -> SyncRun | None:
        """Navbatdagi QUEUED → RUNNING (FOR UPDATE SKIP LOCKED)."""

    async def finish(self, run_id: UUID, *, stats: dict[str, int], error: str | None) -> None: ...


@dataclass(frozen=True, slots=True)
class SyncRunItem:
    id: UUID
    server_code: str
    kind: SyncKind
    status: SyncStatus
    params: dict[str, Any]
    stats: dict[str, int]
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class SyncRunReader(Protocol):
    async def recent(self, *, limit: int) -> list[SyncRunItem]: ...
