"""receiving modulining iiko eksporti uchun public interfeysi (integration_iiko chaqiradi, ARCHITECTURE §3.1).

Kirim statusi qabulning o'zida saqlanadi (ro'yxat / kartochkada ko'rinadi);
integration_iiko faqat shu facade orqali yozadi.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class ExportStatus(StrEnum):
    PENDING = "pending"
    EXPORTED = "exported"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ExportLine:
    product_id: UUID
    qty: Decimal  # qabul qilingan (brak chiqarilgan), bazaviy birlikda
    price: Decimal
    amount: Decimal


@dataclass(frozen=True, slots=True)
class ReceiptForExport:
    id: UUID
    number: str
    store_id: UUID
    supplier_id: UUID
    payment_method: str | None
    received_at: datetime
    supplier_invoice_no: str | None
    had_dispute: bool
    lines: tuple[ExportLine, ...]


class ExportStore(Protocol):
    async def for_export(self, receipt_id: UUID) -> ReceiptForExport | None: ...

    async def record(
        self, receipt_id: UUID, *, status: ExportStatus, document_number: str | None, error: str | None
    ) -> None: ...


class ReceiptExports:
    def __init__(self, store: ExportStore) -> None:
        self._store = store

    async def for_export(self, receipt_id: UUID) -> ReceiptForExport | None:
        return await self._store.for_export(receipt_id)

    async def mark_pending(self, receipt_id: UUID) -> None:
        await self._store.record(receipt_id, status=ExportStatus.PENDING, document_number=None, error=None)

    async def mark_exported(self, receipt_id: UUID, *, document_number: str) -> None:
        await self._store.record(receipt_id, status=ExportStatus.EXPORTED, document_number=document_number, error=None)

    async def mark_failed(self, receipt_id: UUID, *, error: str) -> None:
        await self._store.record(receipt_id, status=ExportStatus.FAILED, document_number=None, error=error[:1000])
