"""Majburiyat va to'lov zayavkasi aggregate'lari."""

from collections.abc import Iterable
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from zakup.modules.finance.domain.finance import (
    ACTIVE_PAYMENT_STATUSES,
    Obligation,
    PaymentLine,
    PaymentMethod,
    PaymentRequest,
    PaymentStatus,
)
from zakup.modules.finance.infrastructure.tables import obligations, payment_lines, payment_number_seq, payment_requests
from zakup.shared_kernel.errors import ConflictError


def _obligation(row: Any) -> Obligation:
    return Obligation(
        id=row.id,
        receipt_id=row.receipt_id,
        receipt_number=row.receipt_number,
        supplier_id=row.supplier_id,
        store_id=row.store_id,
        amount=row.amount,
        paid=row.paid,
        received_on=row.received_on,
        due_date=row.due_date,
        blocked=row.status == "BLOCKED",
        version=row.version,
    )


class SqlObligationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def by_receipt(self, receipt_id: UUID) -> Obligation | None:
        row = (await self._session.execute(select(obligations).where(obligations.c.receipt_id == receipt_id))).first()
        return _obligation(row) if row else None

    async def get_many(self, ids: Iterable[UUID]) -> dict[UUID, Obligation]:
        query = select(obligations).where(obligations.c.id.in_(list(ids))).order_by(obligations.c.id).with_for_update()
        return {row.id: _obligation(row) for row in (await self._session.execute(query)).all()}

    async def add(self, obligation: Obligation) -> None:
        await self._session.execute(
            insert(obligations).values(
                id=obligation.id,
                receipt_id=obligation.receipt_id,
                receipt_number=obligation.receipt_number,
                supplier_id=obligation.supplier_id,
                store_id=obligation.store_id,
                amount=obligation.amount,
                paid=obligation.paid,
                received_on=obligation.received_on,
                due_date=obligation.due_date,
                status=obligation.status.value,
                version=obligation.version,
            )
        )

    async def save(self, obligation: Obligation) -> None:
        result = await self._session.execute(
            update(obligations)
            .where(obligations.c.id == obligation.id, obligations.c.version == obligation.version)
            .values(
                amount=obligation.amount,
                paid=obligation.paid,
                status=obligation.status.value,
                version=obligation.version + 1,
                updated_at=func.now(),
            )
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise ConflictError("payment.modified")
        obligation.version += 1


def _payment_row(payment: PaymentRequest) -> dict[str, Any]:
    return {
        "status": payment.status.value,
        "total": payment.total,
        "approved_by": payment.approved_by,
        "approved_at": payment.approved_at,
        "decision_comment": payment.decision_comment,
        "paid_by": payment.paid_by,
        "paid_at": payment.paid_at,
        "proof_id": payment.proof_id,
    }


class SqlPaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def next_number(self) -> str:
        return f"P-{await self._session.scalar(payment_number_seq.next_value()):06d}"

    async def get(self, payment_id: UUID) -> PaymentRequest | None:
        row = (await self._session.execute(select(payment_requests).where(payment_requests.c.id == payment_id))).first()
        if row is None:
            return None
        lines = await self._session.execute(
            select(payment_lines).where(payment_lines.c.payment_id == payment_id).order_by(payment_lines.c.position)
        )
        return PaymentRequest(
            id=row.id,
            number=row.number,
            supplier_id=row.supplier_id,
            method=PaymentMethod(row.method),
            lines=[PaymentLine(line.obligation_id, line.amount) for line in lines],
            status=PaymentStatus(row.status),
            requested_by=row.requested_by,
            requested_at=row.requested_at,
            comment=row.comment,
            approved_by=row.approved_by,
            approved_at=row.approved_at,
            decision_comment=row.decision_comment,
            paid_by=row.paid_by,
            paid_at=row.paid_at,
            proof_id=row.proof_id,
            version=row.version,
        )

    async def add(self, payment: PaymentRequest) -> None:
        await self._session.execute(
            insert(payment_requests).values(
                id=payment.id,
                number=payment.number,
                supplier_id=payment.supplier_id,
                method=payment.method.value,
                comment=payment.comment,
                requested_by=payment.requested_by,
                requested_at=payment.requested_at,
                version=payment.version,
                **_payment_row(payment),
            )
        )
        await self._session.execute(
            insert(payment_lines),
            [
                {"payment_id": payment.id, "obligation_id": line.obligation_id, "position": i, "amount": line.amount}
                for i, line in enumerate(payment.lines)
            ],
        )

    async def save(self, payment: PaymentRequest) -> None:
        """Qatorlar o'zgarmaydi (o'zgartirish — bekor qilib yangisini tuzish)."""
        result = await self._session.execute(
            update(payment_requests)
            .where(payment_requests.c.id == payment.id, payment_requests.c.version == payment.version)
            .values(**_payment_row(payment), version=payment.version + 1, updated_at=func.now())
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise ConflictError("payment.modified")
        payment.version += 1

    async def reserved(self, obligation_ids: Iterable[UUID], *, exclude: UUID | None = None) -> dict[UUID, Decimal]:
        ids = list(obligation_ids)
        if not ids:
            return {}
        query = (
            select(payment_lines.c.obligation_id, func.sum(payment_lines.c.amount))
            .join(payment_requests, payment_requests.c.id == payment_lines.c.payment_id)
            .where(
                payment_lines.c.obligation_id.in_(ids),
                payment_requests.c.status.in_([s.value for s in ACTIVE_PAYMENT_STATUSES]),
            )
            .group_by(payment_lines.c.obligation_id)
        )
        if exclude is not None:
            query = query.where(payment_requests.c.id != exclude)
        return {row[0]: row[1] for row in (await self._session.execute(query)).all()}
