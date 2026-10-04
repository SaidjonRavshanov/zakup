"""Qabul → iiko kirim nakladnoyi (WORKFLOW B10).

- Navbat: ReceiptAccepted (outbox) → invoice_exports; worker bittadan yuboradi, xatoda — kechikish bilan qayta.
- Idempotentlik: qayta yuborishdan oldin iiko'da shu raqamli (bizning qabul raqami) hujjat qidiriladi —
  oldingi urinish javobsiz qolgan bo'lsa ham dublikat yaratilmaydi.
- Qabul yo'qolmaydi: xato bo'lsa holat "failed", sababi qabul kartochkasida ko'rinadi.
"""

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID

import structlog

from zakup.modules.integration_iiko.application.ports import EntityKind, IikoGateway, Links, ServerInfo
from zakup.modules.integration_iiko.domain.models import IncomingInvoiceDraft, InvoiceDraftItem
from zakup.shared_kernel.clock import Clock, utc_now
from zakup.shared_kernel.errors import DomainError

log = structlog.get_logger()
BACKOFF = (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=30), timedelta(hours=2), timedelta(hours=6))
IIKO_TZ = timedelta(hours=5)  # Toshkent — iiko server vaqti


class ExportMappingError(DomainError):
    """iiko'da mos ombor / tovar / yetkazuvchi topilmadi — ma'lumotnomani tuzatish kerak."""

    code = "iiko_mapping"


@dataclass(frozen=True, slots=True)
class ExportLineData:
    product_id: UUID
    qty: Decimal
    price: Decimal
    amount: Decimal


@dataclass(frozen=True, slots=True)
class ReceiptData:
    id: UUID
    number: str
    store_id: UUID
    supplier_id: UUID
    payment_method: str | None
    received_at: datetime
    supplier_invoice_no: str | None
    had_dispute: bool
    lines: tuple[ExportLineData, ...]


class ReceiptsPort(Protocol):
    """receiving modulining ReceiptExports facade'i."""

    async def for_export(self, receipt_id: UUID) -> ReceiptData | None: ...

    async def mark_pending(self, receipt_id: UUID) -> None: ...

    async def mark_exported(self, receipt_id: UUID, *, document_number: str) -> None: ...

    async def mark_failed(self, receipt_id: UUID, *, error: str) -> None: ...


class BranchPort(Protocol):
    async def store_branch_code(self, store_id: UUID) -> str | None: ...


@dataclass(frozen=True, slots=True)
class ClaimedExport:
    receipt_id: UUID
    attempts: int


class ExportQueue(Protocol):
    async def enqueue(self, receipt_id: UUID) -> None:
        """Takroriy — e'tiborsiz (receipt_id unikal)."""

    async def claim_due(self, now: datetime) -> ClaimedExport | None: ...

    async def finish(
        self,
        receipt_id: UUID,
        *,
        ok: bool,
        error: str | None,
        next_attempt_at: datetime | None,
        document_number: str | None,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class ExportScope:
    queue: ExportQueue
    receipts: ReceiptsPort
    branches: BranchPort
    links: Links
    commit: Callable[[], Awaitable[None]]


class ExportScopeFactory(Protocol):
    def __call__(self) -> AbstractAsyncContextManager[ExportScope]: ...


@dataclass(frozen=True, slots=True)
class ExportSettings:
    post_processed: bool = True  # Tarnov: kirim darhol o'tkaziladi (anketa)
    disputed_processed: bool = False  # nizo bo'lgan qabul — buxgalter tekshiruvi uchun o'tkazilmagan holda


class EnqueueInvoiceExport:
    """Outbox handler: receiving.receipt_accepted."""

    def __init__(self, queue: ExportQueue, receipts: ReceiptsPort) -> None:
        self._queue = queue
        self._receipts = receipts

    async def __call__(self, receipt_id: UUID) -> None:
        await self._queue.enqueue(receipt_id)
        await self._receipts.mark_pending(receipt_id)


class ExportNextInvoice:
    """Worker qadami. True — ish bor edi."""

    def __init__(
        self,
        gateway: IikoGateway,
        scope: ExportScopeFactory,
        settings: ExportSettings,
        clock: Clock = utc_now,
    ) -> None:
        self._gateway = gateway
        self._scope = scope
        self._settings = settings
        self._clock = clock

    async def __call__(self) -> bool:
        async with self._scope() as scope:
            claimed = await scope.queue.claim_due(self._clock())
            await scope.commit()
        if claimed is None:
            return False
        try:
            server, draft = await self._prepare(claimed.receipt_id)
            document_number = await self._send(server, draft)
        except Exception as exc:  # worker yiqilmasin; sabab qabul kartochkasiga yoziladi
            log.warning("iiko_export_failed", receipt_id=str(claimed.receipt_id), error=str(exc))
            await self._finish(claimed, ok=False, error=_describe(exc))
        else:
            log.info("iiko_export_done", receipt_id=str(claimed.receipt_id), document=document_number)
            await self._finish(claimed, ok=True, document_number=document_number)
        return True

    async def _prepare(self, receipt_id: UUID) -> tuple[ServerInfo, IncomingInvoiceDraft]:
        async with self._scope() as scope:
            receipt = await scope.receipts.for_export(receipt_id)
            if receipt is None:
                raise ExportMappingError("iiko.receipt_not_ready")
            branch = await scope.branches.store_branch_code(receipt.store_id)
            server = next((s for s in self._gateway.servers() if branch and s.department_code == branch), None)
            if server is None:
                raise ExportMappingError("iiko.no_server_for_store")
            return server, await self._draft(scope.links, server.code, receipt)

    async def _draft(self, links: Links, server: str, receipt: ReceiptData) -> IncomingInvoiceDraft:
        store = await _one(links, server, EntityKind.STORE, receipt.store_id, "iiko.store_not_linked")
        supplier = await self._supplier(links, server, receipt)
        items = []
        for line in receipt.lines:
            product = await _one(links, server, EntityKind.PRODUCT, line.product_id, "iiko.product_not_linked")
            items.append(InvoiceDraftItem(product, store, line.qty, line.price, line.amount))
        processed = self._settings.disputed_processed if receipt.had_dispute else self._settings.post_processed
        method = {"cash": "нал", "transfer": "пер"}.get(receipt.payment_method or "", "")
        return IncomingInvoiceDraft(
            document_number=receipt.number,
            incoming_at=(receipt.received_at + IIKO_TZ).strftime("%Y-%m-%dT%H:%M:%S"),
            supplier_id=supplier,
            store_id=store,
            supplier_invoice_no=receipt.supplier_invoice_no,
            comment=" ".join(filter(None, ["Zakup", receipt.number, method])),
            processed=processed,
            items=tuple(items),
        )

    @staticmethod
    async def _supplier(links: Links, server: str, receipt: ReceiptData) -> UUID:
        """НАЛ / ПЕР kartochkasi — qabuldagi to'lov usuli bo'yicha; bo'lmasa — istalgani."""
        candidates = await links.iiko_ids(server, EntityKind.SUPPLIER, receipt.supplier_id)
        if not candidates:
            raise ExportMappingError("iiko.supplier_not_linked")
        for iiko_id, attrs in candidates:
            if receipt.payment_method and attrs.get("payment_method") == receipt.payment_method:
                return iiko_id
        return candidates[0][0]

    async def _send(self, server: ServerInfo, draft: IncomingInvoiceDraft) -> str:
        day = datetime.fromisoformat(draft.incoming_at).date()
        async with self._gateway.session(server.code) as iiko:
            existing = await iiko.incoming_invoices(day - timedelta(days=1), day + timedelta(days=1))
            if any(invoice.number == draft.document_number for invoice in existing):
                return draft.document_number  # oldingi urinish o'tgan — dublikat yaratmaymiz
            result = await iiko.import_incoming_invoice(draft)
        if not result.valid:
            raise ExportMappingError("iiko.import_rejected", error=result.error or "?")
        return result.document_number or draft.document_number

    async def _finish(
        self, claimed: ClaimedExport, *, ok: bool, error: str | None = None, document_number: str | None = None
    ) -> None:
        attempts = claimed.attempts + 1
        next_at = None if ok else self._clock() + BACKOFF[min(attempts, len(BACKOFF)) - 1]
        async with self._scope() as scope:
            await scope.queue.finish(
                claimed.receipt_id, ok=ok, error=error, next_attempt_at=next_at, document_number=document_number
            )
            if ok and document_number:
                await scope.receipts.mark_exported(claimed.receipt_id, document_number=document_number)
            else:
                await scope.receipts.mark_failed(claimed.receipt_id, error=error or "?")
            await scope.commit()


async def _one(links: Links, server: str, kind: EntityKind, local_id: UUID, key: str) -> UUID:
    found = await links.iiko_ids(server, kind, local_id)
    if not found:
        raise ExportMappingError(key)
    return found[0][0]


def _describe(exc: Exception) -> str:
    if isinstance(exc, DomainError):
        params = ", ".join(f"{k}={v}" for k, v in exc.params.items())
        return f"{exc.key}{f' ({params})' if params else ''}"
    return f"{type(exc).__name__}: {exc}"[:1000]
