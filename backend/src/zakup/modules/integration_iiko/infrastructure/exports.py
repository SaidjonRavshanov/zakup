"""Kirim eksporti: navbat (SQL) va boshqa modullar facade'lariga adapterlar."""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from zakup.modules.catalog.application.queries import CatalogQueries
from zakup.modules.integration_iiko.application.exports import ClaimedExport, ExportLineData, ReceiptData
from zakup.modules.integration_iiko.infrastructure.tables import invoice_exports
from zakup.modules.receiving.application.exports import ReceiptExports

STUCK_AFTER = timedelta(minutes=10)


class SqlExportQueue:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(self, receipt_id: UUID) -> None:
        await self._session.execute(
            insert(invoice_exports).values(receipt_id=receipt_id).on_conflict_do_nothing(index_elements=["receipt_id"])
        )

    async def claim_due(self, now: datetime) -> ClaimedExport | None:
        query = (
            select(invoice_exports.c.receipt_id, invoice_exports.c.attempts)
            .where(
                or_(
                    (invoice_exports.c.next_attempt_at <= now) & invoice_exports.c.status.in_(["queued", "failed"]),
                    # worker ish o'rtasida to'xtagan bo'lsa — 10 daqiqadan keyin qayta olinadi
                    (invoice_exports.c.status == "running") & (invoice_exports.c.updated_at < now - STUCK_AFTER),
                )
            )
            .order_by(invoice_exports.c.next_attempt_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        row = (await self._session.execute(query)).first()
        if row is None:
            return None
        await self._session.execute(
            update(invoice_exports)
            .where(invoice_exports.c.receipt_id == row.receipt_id)
            .values(status="running", updated_at=now)
        )
        return ClaimedExport(receipt_id=row.receipt_id, attempts=row.attempts)

    async def finish(
        self,
        receipt_id: UUID,
        *,
        ok: bool,
        error: str | None,
        next_attempt_at: datetime | None,
        document_number: str | None,
    ) -> None:
        values: dict[str, object] = {
            "status": "done" if ok else "failed",
            "attempts": invoice_exports.c.attempts + 1,
            "last_error": error,
            "document_number": document_number,
            "updated_at": datetime.now().astimezone(),
        }
        if next_attempt_at is not None:
            values["next_attempt_at"] = next_attempt_at
        await self._session.execute(
            update(invoice_exports).where(invoice_exports.c.receipt_id == receipt_id).values(**values)
        )


class ReceiptsAdapter:
    def __init__(self, exports: ReceiptExports) -> None:
        self._exports = exports

    async def for_export(self, receipt_id: UUID) -> ReceiptData | None:
        receipt = await self._exports.for_export(receipt_id)
        if receipt is None:
            return None
        return ReceiptData(
            id=receipt.id,
            number=receipt.number,
            store_id=receipt.store_id,
            supplier_id=receipt.supplier_id,
            payment_method=receipt.payment_method,
            received_at=receipt.received_at,
            supplier_invoice_no=receipt.supplier_invoice_no,
            had_dispute=receipt.had_dispute,
            lines=tuple(ExportLineData(line.product_id, line.qty, line.price, line.amount) for line in receipt.lines),
        )

    async def mark_pending(self, receipt_id: UUID) -> None:
        await self._exports.mark_pending(receipt_id)

    async def mark_exported(self, receipt_id: UUID, *, document_number: str) -> None:
        await self._exports.mark_exported(receipt_id, document_number=document_number)

    async def mark_failed(self, receipt_id: UUID, *, error: str) -> None:
        await self._exports.mark_failed(receipt_id, error=error)


class BranchAdapter:
    def __init__(self, catalog: CatalogQueries) -> None:
        self._catalog = catalog

    async def store_branch_code(self, store_id: UUID) -> str | None:
        return await self._catalog.store_branch_code(store_id)
