"""O'qish tomoni: faqat finance jadvallari; nomlar — catalog facade orqali (use case'da)."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from zakup.modules.finance.application.dto import ObligationView, PaymentDetail, PaymentLineView, PaymentListItem
from zakup.modules.finance.domain.finance import ObligationStatus, PaymentMethod, PaymentStatus
from zakup.modules.finance.infrastructure.tables import obligations, payment_lines, payment_requests


def _obligation(row: Any) -> ObligationView:
    return ObligationView(
        id=row.id,
        receipt_id=row.receipt_id,
        receipt_number=row.receipt_number,
        supplier_id=row.supplier_id,
        store_id=row.store_id,
        amount=row.amount,
        paid=row.paid,
        outstanding=row.amount - row.paid,
        received_on=row.received_on,
        due_date=row.due_date,
        status=ObligationStatus(row.status),
    )


def _list_item(row: Any) -> PaymentListItem:
    return PaymentListItem(
        id=row.id,
        number=row.number,
        supplier_id=row.supplier_id,
        method=PaymentMethod(row.method),
        status=PaymentStatus(row.status),
        total=row.total,
        requested_at=row.requested_at,
        paid_at=row.paid_at,
    )


class SqlFinanceReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def obligations(
        self, *, supplier_id: UUID | None, store_ids: set[UUID] | None, unpaid_only: bool
    ) -> list[ObligationView]:
        query = select(obligations).order_by(obligations.c.due_date, obligations.c.receipt_number)
        if supplier_id is not None:
            query = query.where(obligations.c.supplier_id == supplier_id)
        if store_ids is not None:
            query = query.where(obligations.c.store_id.in_(store_ids))
        if unpaid_only:
            query = query.where(obligations.c.status != ObligationStatus.PAID.value)
        return [_obligation(row) for row in (await self._session.execute(query)).all()]

    async def payments(
        self, *, statuses: set[PaymentStatus] | None, supplier_id: UUID | None, limit: int
    ) -> list[PaymentListItem]:
        query = select(payment_requests).order_by(payment_requests.c.requested_at.desc(), payment_requests.c.id.desc())
        if statuses:
            query = query.where(payment_requests.c.status.in_([s.value for s in statuses]))
        if supplier_id is not None:
            query = query.where(payment_requests.c.supplier_id == supplier_id)
        return [_list_item(row) for row in (await self._session.execute(query.limit(limit))).all()]

    async def payment(self, payment_id: UUID) -> PaymentDetail | None:
        row = (await self._session.execute(select(payment_requests).where(payment_requests.c.id == payment_id))).first()
        if row is None:
            return None
        lines = await self._session.execute(
            select(
                payment_lines.c.amount.label("line_amount"),
                obligations.c.id,
                obligations.c.receipt_id,
                obligations.c.receipt_number,
                (obligations.c.amount - obligations.c.paid).label("outstanding"),
            )
            .join(obligations, obligations.c.id == payment_lines.c.obligation_id)
            .where(payment_lines.c.payment_id == payment_id)
            .order_by(payment_lines.c.position)
        )
        return PaymentDetail(
            id=row.id,
            number=row.number,
            supplier_id=row.supplier_id,
            method=PaymentMethod(row.method),
            status=PaymentStatus(row.status),
            total=row.total,
            requested_by=row.requested_by,
            requested_at=row.requested_at,
            comment=row.comment,
            approved_by=row.approved_by,
            approved_at=row.approved_at,
            decision_comment=row.decision_comment,
            paid_by=row.paid_by,
            paid_at=row.paid_at,
            proof_id=row.proof_id,
            lines=tuple(
                PaymentLineView(
                    obligation_id=line.id,
                    receipt_id=line.receipt_id,
                    receipt_number=line.receipt_number,
                    amount=line.line_amount,
                    outstanding=line.outstanding,
                )
                for line in lines
            ),
        )
