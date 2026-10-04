"""receiving port'lari. procurement va catalog bilan — faqat ularning public interfeysi orqali (adapterlar)."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from zakup.modules.receiving.application.dto import ReceiptDetail, ReceiptListItem
from zakup.modules.receiving.domain.receipt import Receipt, ReceiptStatus


class ReceiptRepository(Protocol):
    async def next_number(self) -> str: ...

    async def get(self, receipt_id: UUID) -> Receipt | None: ...

    async def find_by_order(self, order_id: UUID) -> Receipt | None: ...

    async def add(self, receipt: Receipt) -> None: ...

    async def save(self, receipt: Receipt) -> None: ...


@dataclass(frozen=True, slots=True)
class ExpectedOrderLine:
    order_line_id: UUID
    product_id: UUID
    product_name: str
    base_unit: str
    qty: Decimal
    price: Decimal


@dataclass(frozen=True, slots=True)
class ExpectedOrder:
    order_id: UUID
    number: str
    store_id: UUID
    supplier_id: UUID
    lines: tuple[ExpectedOrderLine, ...]


class OrdersPort(Protocol):
    async def expected(self, order_id: UUID) -> ExpectedOrder: ...

    async def mark_received(self, order_id: UUID, *, complete: bool) -> None: ...


class LabelsPort(Protocol):
    async def labels(
        self, *, products: Iterable[UUID] = (), suppliers: Iterable[UUID] = (), stores: Iterable[UUID] = ()
    ) -> tuple[dict[UUID, str], dict[UUID, str], dict[UUID, str]]:
        """(tovarlar, yetkazuvchilar, omborlar) nomlari."""


@dataclass(frozen=True, slots=True)
class StoredFile:
    id: UUID
    content_type: str
    content: bytes


class Attachments(Protocol):
    """Fayllar (nakladnoy fotosi): hozir lokal disk, keyin S3 (ARCHITECTURE §7)."""

    async def store(self, *, content: bytes, content_type: str, uploaded_by: UUID, at: datetime) -> UUID: ...

    async def exists(self, file_id: UUID) -> bool: ...

    async def load(self, file_id: UUID) -> StoredFile | None: ...


class ReceiptReader(Protocol):
    async def list(
        self, *, store_ids: set[UUID] | None, statuses: set[ReceiptStatus] | None, limit: int
    ) -> list[ReceiptListItem]: ...

    async def detail(self, receipt_id: UUID) -> ReceiptDetail | None: ...
