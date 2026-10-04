"""Qabul aggregate'i (sarlavha + qatorlar + farqlar), fayllar, iiko eksport holati."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, insert, select, update
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from zakup.modules.receiving.application.exports import ExportLine, ExportStatus, ReceiptForExport
from zakup.modules.receiving.application.ports import StoredFile
from zakup.modules.receiving.domain.receipt import (
    Discrepancy,
    DiscrepancyKind,
    Dispute,
    PaymentMethod,
    Receipt,
    ReceiptHeader,
    ReceiptLine,
    ReceiptStatus,
    Resolution,
)
from zakup.modules.receiving.infrastructure.tables import (
    attachments,
    discrepancies,
    receipt_lines,
    receipt_number_seq,
    receipts,
)
from zakup.shared_kernel.errors import ConflictError
from zakup.shared_kernel.ids import new_id

_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "application/pdf": ".pdf"}


def _header_row(receipt: Receipt) -> dict[str, Any]:
    h, d = receipt.header, receipt.dispute
    return {
        "status": receipt.status.value,
        "supplier_invoice_no": h.supplier_invoice_no,
        "payment_method": h.payment_method.value if h.payment_method else None,
        "comment": h.comment,
        "total": receipt.total,
        "expected_total": receipt.expected_total,
        "dispute_opened_at": d.opened_at if d else None,
        "dispute_resolution": d.resolution.value if d and d.resolution else None,
        "dispute_comment": d.comment if d else None,
        "dispute_resolved_by": d.resolved_by if d else None,
        "dispute_resolved_at": d.resolved_at if d else None,
    }


def _dispute(row: Row[Any]) -> Dispute | None:
    if row.dispute_opened_at is None:
        return None
    return Dispute(
        opened_at=row.dispute_opened_at,
        resolution=Resolution(row.dispute_resolution) if row.dispute_resolution else None,
        comment=row.dispute_comment,
        resolved_by=row.dispute_resolved_by,
        resolved_at=row.dispute_resolved_at,
    )


class SqlReceiptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def next_number(self) -> str:
        return f"R-{await self._session.scalar(receipt_number_seq.next_value()):06d}"

    async def get(self, receipt_id: UUID) -> Receipt | None:
        return await self._load(receipts.c.id == receipt_id)

    async def find_by_order(self, order_id: UUID) -> Receipt | None:
        return await self._load(receipts.c.order_id == order_id)

    async def add(self, receipt: Receipt) -> None:
        h = receipt.header
        await self._session.execute(
            insert(receipts).values(
                id=receipt.id,
                number=receipt.number,
                order_id=h.order_id,
                store_id=h.store_id,
                supplier_id=h.supplier_id,
                received_by=h.received_by,
                received_at=h.received_at,
                invoice_photo_id=h.invoice_photo_id,
                version=receipt.version,
                **_header_row(receipt),
            )
        )
        await self._session.execute(
            insert(receipt_lines),
            [
                {
                    "id": line.id,
                    "receipt_id": receipt.id,
                    "position": position,
                    "order_line_id": line.order_line_id,
                    "product_id": line.product_id,
                    "base_unit": line.base_unit,
                    "qty_expected": line.qty_expected,
                    "price_expected": line.price_expected,
                    "qty_fact": line.qty_fact,
                    "price_fact": line.price_fact,
                    "qty_defect": line.qty_defect,
                    "defect_reason": line.defect_reason,
                }
                for position, line in enumerate(receipt.lines)
            ],
        )
        if receipt.discrepancies:
            await self._session.execute(
                insert(discrepancies),
                [
                    {
                        "id": new_id(),
                        "receipt_id": receipt.id,
                        "line_id": d.line_id,
                        "kind": d.kind.value,
                        "expected": d.expected,
                        "actual": d.actual,
                        "within_tolerance": d.within_tolerance,
                    }
                    for d in receipt.discrepancies
                ],
            )

    async def save(self, receipt: Receipt) -> None:
        """Faqat sarlavha o'zgaradi (nizo yechimi); qatorlar — o'zgarmas (tuzatish — yangi versiya)."""
        result = await self._session.execute(
            update(receipts)
            .where(receipts.c.id == receipt.id, receipts.c.version == receipt.version)
            .values(**_header_row(receipt), version=receipt.version + 1, updated_at=func.now())
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise ConflictError("receipt.modified")
        receipt.version += 1

    async def _load(self, condition: Any) -> Receipt | None:
        row = (await self._session.execute(select(receipts).where(condition))).first()
        if row is None:
            return None
        lines = await self._session.execute(
            select(receipt_lines).where(receipt_lines.c.receipt_id == row.id).order_by(receipt_lines.c.position)
        )
        found = await self._session.execute(select(discrepancies).where(discrepancies.c.receipt_id == row.id))
        return Receipt(
            id=row.id,
            number=row.number,
            header=ReceiptHeader(
                order_id=row.order_id,
                store_id=row.store_id,
                supplier_id=row.supplier_id,
                received_by=row.received_by,
                received_at=row.received_at,
                supplier_invoice_no=row.supplier_invoice_no,
                payment_method=PaymentMethod(row.payment_method) if row.payment_method else None,
                invoice_photo_id=row.invoice_photo_id,
                comment=row.comment,
            ),
            status=ReceiptStatus(row.status),
            lines=[
                ReceiptLine(
                    id=line.id,
                    order_line_id=line.order_line_id,
                    product_id=line.product_id,
                    base_unit=line.base_unit,
                    qty_expected=line.qty_expected,
                    price_expected=line.price_expected,
                    qty_fact=line.qty_fact,
                    price_fact=line.price_fact,
                    qty_defect=line.qty_defect,
                    defect_reason=line.defect_reason,
                )
                for line in lines
            ],
            discrepancies=[
                Discrepancy(d.line_id, DiscrepancyKind(d.kind), d.expected, d.actual, d.within_tolerance) for d in found
            ],
            dispute=_dispute(row),
            version=row.version,
        )


class LocalAttachments:
    """Lokal disk: {media_dir}/{yyyy}/{mm}/{sha256}{ext}. Production'da — S3 (ARCHITECTURE §7)."""

    def __init__(self, session: AsyncSession, media_dir: Path) -> None:
        self._session = session
        self._media_dir = media_dir

    async def store(self, *, content: bytes, content_type: str, uploaded_by: UUID, at: datetime) -> UUID:
        digest = hashlib.sha256(content).hexdigest()
        key = f"{at:%Y/%m}/{digest}{_EXT.get(content_type, '')}"
        path = self._media_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(content)
        file_id = new_id()
        await self._session.execute(
            insert(attachments).values(
                id=file_id,
                content_type=content_type,
                size=len(content),
                sha256=digest,
                storage_key=key,
                uploaded_by=uploaded_by,
            )
        )
        return file_id

    async def exists(self, file_id: UUID) -> bool:
        return bool(await self._session.scalar(select(func.count()).where(attachments.c.id == file_id)))

    async def load(self, file_id: UUID) -> StoredFile | None:
        row = (await self._session.execute(select(attachments).where(attachments.c.id == file_id))).first()
        if row is None:
            return None
        path = self._media_dir / row.storage_key
        if not path.is_file():
            return None
        return StoredFile(id=row.id, content_type=row.content_type, content=path.read_bytes())


class SqlExportStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def for_export(self, receipt_id: UUID) -> ReceiptForExport | None:
        row = (await self._session.execute(select(receipts).where(receipts.c.id == receipt_id))).first()
        if row is None or row.status != ReceiptStatus.ACCEPTED.value:
            return None
        lines = await self._session.execute(
            select(receipt_lines).where(receipt_lines.c.receipt_id == receipt_id).order_by(receipt_lines.c.position)
        )
        export_lines = []
        for line in lines:
            qty = max(line.qty_fact - line.qty_defect, 0)
            if qty > 0:
                export_lines.append(
                    ExportLine(
                        product_id=line.product_id,
                        qty=qty,
                        price=line.price_fact,
                        amount=round(qty * line.price_fact, 2),
                    )
                )
        return ReceiptForExport(
            id=row.id,
            number=row.number,
            store_id=row.store_id,
            supplier_id=row.supplier_id,
            payment_method=row.payment_method,
            received_at=row.received_at,
            supplier_invoice_no=row.supplier_invoice_no,
            had_dispute=row.dispute_opened_at is not None,
            lines=tuple(export_lines),
        )

    async def record(
        self, receipt_id: UUID, *, status: ExportStatus, document_number: str | None, error: str | None
    ) -> None:
        await self._session.execute(
            update(receipts)
            .where(receipts.c.id == receipt_id)
            .values(
                iiko_status=status.value, iiko_document_number=document_number, iiko_error=error, updated_at=func.now()
            )
        )
