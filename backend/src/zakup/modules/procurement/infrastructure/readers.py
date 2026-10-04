"""O'qish tomoni (CQRS-lite): faqat procurement jadvallari; nomlar (tovar, ombor) — use case'da catalog'dan."""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession

from zakup.modules.procurement.application.dto import (
    ApprovalView,
    OrderDetail,
    OrderLineView,
    OrderListItem,
    RequestDetail,
    RequestLineView,
    RequestListItem,
)
from zakup.modules.procurement.domain.approval import Decision
from zakup.modules.procurement.domain.order import Channel, OrderStatus, ResponseKind
from zakup.modules.procurement.domain.request import LineDecision, RequestStatus, RequestType
from zakup.modules.procurement.infrastructure.tables import (
    approvals,
    purchase_order_lines,
    purchase_orders,
    purchase_request_lines,
    purchase_requests,
)

MONEY = Decimal("0.01")


class SqlRequestReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self, *, statuses: set[RequestStatus] | None, store_ids: set[UUID] | None, initiator_id: UUID | None, limit: int
    ) -> list[RequestListItem]:
        lines_count = (
            select(func.count()).where(purchase_request_lines.c.request_id == purchase_requests.c.id).scalar_subquery()
        )
        query = select(purchase_requests, lines_count.label("lines_count")).order_by(
            purchase_requests.c.created_at.desc(), purchase_requests.c.id.desc()
        )
        if statuses:
            query = query.where(purchase_requests.c.status.in_([s.value for s in statuses]))
        if store_ids is not None:
            query = query.where(purchase_requests.c.store_id.in_(store_ids))
        if initiator_id is not None:
            query = query.where(purchase_requests.c.initiator_id == initiator_id)
        rows = (await self._session.execute(query.limit(limit))).all()
        return [
            RequestListItem(
                id=row.id,
                number=row.number,
                store_id=row.store_id,
                type=RequestType(row.type),
                status=RequestStatus(row.status),
                needed_by=row.needed_by,
                initiator_id=row.initiator_id,
                total=row.total_amount,
                lines_count=row.lines_count,
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def detail(self, request_id: UUID) -> RequestDetail | None:
        row = (
            await self._session.execute(select(purchase_requests).where(purchase_requests.c.id == request_id))
        ).first()
        if row is None:
            return None
        lines = await self._session.execute(
            select(purchase_request_lines)
            .where(purchase_request_lines.c.request_id == request_id)
            .order_by(purchase_request_lines.c.position)
        )
        records = await self._session.execute(
            select(approvals).where(approvals.c.request_id == request_id).order_by(approvals.c.decided_at)
        )
        return RequestDetail(
            id=row.id,
            number=row.number,
            store_id=row.store_id,
            type=RequestType(row.type),
            status=RequestStatus(row.status),
            needed_by=row.needed_by,
            initiator_id=row.initiator_id,
            comment=row.comment,
            total=row.total_amount,
            created_at=row.created_at,
            version=row.version,
            lines=tuple(
                RequestLineView(
                    id=line.id,
                    product_id=line.product_id,
                    qty=line.qty,
                    note=line.note,
                    offer_id=line.offer_id,
                    supplier_id=line.supplier_id,
                    price_per_base=line.price_per_base,
                    amount=(line.qty * line.price_per_base).quantize(MONEY, ROUND_HALF_UP)
                    if line.price_per_base is not None
                    else Decimal(0),
                    decision=LineDecision(line.decision),
                    qty_suggested=line.qty_suggested,
                    calc=line.calc,
                )
                for line in lines
            ),
            approvals=tuple(
                ApprovalView(
                    approver_id=r.approver_id,
                    decision=Decision(r.decision),
                    comment=r.comment,
                    amount=r.amount,
                    role_conflict=r.role_conflict,
                    decided_at=r.decided_at,
                )
                for r in records
            ),
        )


def _order_item(row: Row[Any]) -> OrderListItem:
    return OrderListItem(
        id=row.id,
        number=row.number,
        request_id=row.request_id,
        supplier_id=row.supplier_id,
        store_id=row.store_id,
        delivery_date=row.delivery_date,
        status=OrderStatus(row.status),
        total=row.total_amount,
        confirmed_total=row.confirmed_total,
        lines_count=row.lines_count,
        sent_at=row.sent_at,
        response_deadline=row.response_deadline,
        created_at=row.created_at,
    )


class SqlOrderReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base(self) -> Select[Any]:
        lines_count = (
            select(func.count()).where(purchase_order_lines.c.order_id == purchase_orders.c.id).scalar_subquery()
        )
        return select(purchase_orders, lines_count.label("lines_count"))

    async def list(
        self, *, statuses: set[OrderStatus] | None, store_ids: set[UUID] | None, request_id: UUID | None, limit: int
    ) -> list[OrderListItem]:
        query = self._base().order_by(purchase_orders.c.created_at.desc(), purchase_orders.c.id.desc())
        if statuses:
            query = query.where(purchase_orders.c.status.in_([s.value for s in statuses]))
        if store_ids is not None:
            query = query.where(purchase_orders.c.store_id.in_(store_ids))
        if request_id is not None:
            query = query.where(purchase_orders.c.request_id == request_id)
        return [_order_item(row) for row in (await self._session.execute(query.limit(limit))).all()]

    async def detail(self, order_id: UUID) -> OrderDetail | None:
        row = (await self._session.execute(self._base().where(purchase_orders.c.id == order_id))).first()
        if row is None:
            return None
        lines = await self._session.execute(
            select(purchase_order_lines)
            .where(purchase_order_lines.c.order_id == order_id)
            .order_by(purchase_order_lines.c.position)
        )
        return OrderDetail(
            id=row.id,
            number=row.number,
            request_id=row.request_id,
            supplier_id=row.supplier_id,
            store_id=row.store_id,
            delivery_date=row.delivery_date,
            status=OrderStatus(row.status),
            total=row.total_amount,
            confirmed_total=row.confirmed_total,
            sent_at=row.sent_at,
            sent_channel=Channel(row.sent_channel) if row.sent_channel else None,
            response_deadline=row.response_deadline,
            responded_at=row.responded_at,
            cancel_reason=row.cancel_reason,
            created_at=row.created_at,
            version=row.version,
            lines=tuple(
                OrderLineView(
                    id=line.id,
                    product_id=line.product_id,
                    offer_id=line.offer_id,
                    pack_unit=line.pack_unit,
                    pack_factor=line.pack_factor,
                    qty_packs=line.qty_packs,
                    price_per_pack=line.price_per_pack,
                    amount=(line.qty_packs * line.price_per_pack).quantize(MONEY, ROUND_HALF_UP),
                    response=ResponseKind(line.response) if line.response else None,
                    qty_confirmed=line.qty_confirmed,
                    price_confirmed=line.price_confirmed,
                    needs_reapproval=line.needs_reapproval,
                )
                for line in lines
            ),
        )
