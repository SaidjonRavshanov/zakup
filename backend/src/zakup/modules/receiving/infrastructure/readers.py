"""O'qish tomoni: faqat receiving jadvallari; buyurtma raqami — procurement facade'dan emas, saqlangan qatordan."""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from zakup.modules.receiving.application.dto import (
    DiscrepancyView,
    DisputeView,
    ReceiptDetail,
    ReceiptLineView,
    ReceiptListItem,
)
from zakup.modules.receiving.domain.receipt import DiscrepancyKind, PaymentMethod, ReceiptStatus, Resolution
from zakup.modules.receiving.infrastructure.tables import discrepancies, receipt_lines, receipts

MONEY = Decimal("0.01")


def _list_item(row: Row[Any]) -> ReceiptListItem:
    return ReceiptListItem(
        id=row.id,
        number=row.number,
        order_id=row.order_id,
        order_number=None,
        store_id=row.store_id,
        supplier_id=row.supplier_id,
        status=ReceiptStatus(row.status),
        total=row.total,
        expected_total=row.expected_total,
        received_at=row.received_at,
        dispute_open=row.dispute_opened_at is not None and row.dispute_resolution is None,
        export_status=row.iiko_status,
    )


class SqlReceiptReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self, *, store_ids: set[UUID] | None, statuses: set[ReceiptStatus] | None, limit: int
    ) -> list[ReceiptListItem]:
        query = select(receipts).order_by(receipts.c.received_at.desc(), receipts.c.id.desc())
        if store_ids is not None:
            query = query.where(receipts.c.store_id.in_(store_ids))
        if statuses:
            query = query.where(receipts.c.status.in_([s.value for s in statuses]))
        return [_list_item(row) for row in (await self._session.execute(query.limit(limit))).all()]

    async def detail(self, receipt_id: UUID) -> ReceiptDetail | None:
        row = (await self._session.execute(select(receipts).where(receipts.c.id == receipt_id))).first()
        if row is None:
            return None
        lines = await self._session.execute(
            select(receipt_lines).where(receipt_lines.c.receipt_id == receipt_id).order_by(receipt_lines.c.position)
        )
        found = await self._session.execute(select(discrepancies).where(discrepancies.c.receipt_id == receipt_id))
        dispute = None
        if row.dispute_opened_at is not None:
            dispute = DisputeView(
                opened_at=row.dispute_opened_at,
                resolution=Resolution(row.dispute_resolution) if row.dispute_resolution else None,
                comment=row.dispute_comment,
                resolved_by=row.dispute_resolved_by,
                resolved_at=row.dispute_resolved_at,
            )
        return ReceiptDetail(
            id=row.id,
            number=row.number,
            order_id=row.order_id,
            order_number=None,
            store_id=row.store_id,
            supplier_id=row.supplier_id,
            status=ReceiptStatus(row.status),
            received_by=row.received_by,
            received_at=row.received_at,
            supplier_invoice_no=row.supplier_invoice_no,
            payment_method=PaymentMethod(row.payment_method) if row.payment_method else None,
            invoice_photo_id=row.invoice_photo_id,
            comment=row.comment,
            paid_on_delivery=row.paid_on_delivery,
            total=row.total,
            expected_total=row.expected_total,
            lines=tuple(
                ReceiptLineView(
                    id=line.id,
                    product_id=line.product_id,
                    base_unit=line.base_unit,
                    qty_expected=line.qty_expected,
                    price_expected=line.price_expected,
                    qty_fact=line.qty_fact,
                    price_fact=line.price_fact,
                    qty_defect=line.qty_defect,
                    defect_reason=line.defect_reason,
                    amount=(max(line.qty_fact - line.qty_defect, 0) * line.price_fact).quantize(MONEY, ROUND_HALF_UP),
                )
                for line in lines
            ),
            discrepancies=tuple(
                DiscrepancyView(d.line_id, DiscrepancyKind(d.kind), d.expected, d.actual, d.within_tolerance)
                for d in found
            ),
            dispute=dispute,
            export_status=row.iiko_status,
            export_error=row.iiko_error,
            iiko_document_number=row.iiko_document_number,
        )
