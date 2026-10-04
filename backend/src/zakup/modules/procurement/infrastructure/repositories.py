"""Yozish tomoni: zayavka va PO aggregate'lari (sarlavha + qatorlar) — optimistic lock bilan."""

import hashlib
import secrets
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Table, delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from zakup.modules.procurement.domain.approval import ApprovalRecord, Decision
from zakup.modules.procurement.domain.order import (
    Channel,
    OrderLine,
    OrderStatus,
    PurchaseOrder,
    ResponseKind,
)
from zakup.modules.procurement.domain.request import (
    LineDecision,
    OfferChoice,
    PurchaseRequest,
    RequestLine,
    RequestStatus,
    RequestType,
)
from zakup.modules.procurement.infrastructure.tables import (
    approvals,
    order_number_seq,
    purchase_order_lines,
    purchase_orders,
    purchase_request_lines,
    purchase_requests,
    request_number_seq,
    supplier_response_tokens,
)
from zakup.shared_kernel.errors import ConflictError
from zakup.shared_kernel.ids import new_id


async def _sync_lines(
    session: AsyncSession, table: Table, parent_column: str, parent_id: UUID, rows: list[dict[str, Any]]
) -> None:
    """Qatorlar: yo'qolganlari o'chiriladi, qolganlari upsert.

    ID barqaror — PO qatorlari zayavka qatoriga bog'langan.
    """
    ids = [row["id"] for row in rows]
    await session.execute(delete(table).where(table.c[parent_column] == parent_id, table.c.id.not_in(ids)))
    if rows:
        statement = pg_insert(table).values(rows)
        columns = {key: statement.excluded[key] for key in rows[0] if key != "id"}
        await session.execute(statement.on_conflict_do_update(index_elements=["id"], set_=columns))


async def _bump(
    session: AsyncSession, table: Table, entity_id: UUID, version: int, *, values: dict[str, Any], conflict: str
) -> None:
    result = await session.execute(
        update(table)
        .where(table.c.id == entity_id, table.c.version == version)
        .values(**values, version=version + 1, updated_at=func.now())
    )
    if result.rowcount != 1:  # type: ignore[attr-defined]
        raise ConflictError(conflict)


# ---------------------------------------------------------------- zayavka


def _request_row(request: PurchaseRequest) -> dict[str, Any]:
    return {
        "store_id": request.store_id,
        "type": request.type.value,
        "status": request.status.value,
        "needed_by": request.needed_by,
        "initiator_id": request.initiator_id,
        "comment": request.comment,
        "total_amount": request.total,
        "submitted_at": request.submitted_at,
    }


def _request_lines(request: PurchaseRequest) -> list[dict[str, Any]]:
    return [
        {
            "id": line.id,
            "request_id": request.id,
            "position": position,
            "product_id": line.product_id,
            "qty": line.qty,
            "note": line.note,
            "offer_id": line.offer.offer_id if line.offer else None,
            "supplier_id": line.offer.supplier_id if line.offer else None,
            "price_per_base": line.offer.price_per_base if line.offer else None,
            "decision": line.decision.value,
        }
        for position, line in enumerate(request.lines)
    ]


class SqlRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def next_number(self) -> str:
        return f"Z-{await self._session.scalar(request_number_seq.next_value()):06d}"

    async def get(self, request_id: UUID) -> PurchaseRequest | None:
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
        return PurchaseRequest(
            id=row.id,
            number=row.number,
            store_id=row.store_id,
            type=RequestType(row.type),
            status=RequestStatus(row.status),
            needed_by=row.needed_by,
            initiator_id=row.initiator_id,
            comment=row.comment,
            submitted_at=row.submitted_at,
            version=row.version,
            lines=[
                RequestLine(
                    id=line.id,
                    product_id=line.product_id,
                    qty=line.qty,
                    note=line.note,
                    offer=OfferChoice(line.offer_id, line.supplier_id, line.price_per_base) if line.offer_id else None,
                    decision=LineDecision(line.decision),
                )
                for line in lines
            ],
            approvals=[
                ApprovalRecord(
                    approver_id=r.approver_id,
                    decision=Decision(r.decision),
                    comment=r.comment,
                    amount=r.amount,
                    role_conflict=r.role_conflict,
                    decided_at=r.decided_at,
                )
                for r in records
            ],
        )

    async def add(self, request: PurchaseRequest) -> None:
        await self._session.execute(
            insert(purchase_requests).values(
                id=request.id, number=request.number, version=request.version, **_request_row(request)
            )
        )
        await _sync_lines(self._session, purchase_request_lines, "request_id", request.id, _request_lines(request))
        await self._write_approvals(request)

    async def save(self, request: PurchaseRequest) -> None:
        await _bump(
            self._session,
            purchase_requests,
            request.id,
            request.version,
            values=_request_row(request),
            conflict="request.modified",
        )
        request.version += 1
        await _sync_lines(self._session, purchase_request_lines, "request_id", request.id, _request_lines(request))
        await self._write_approvals(request)

    async def _write_approvals(self, request: PurchaseRequest) -> None:
        records = request.pull_new_approvals()
        if records:
            await self._session.execute(
                insert(approvals),
                [
                    {
                        "id": new_id(),
                        "request_id": request.id,
                        "approver_id": r.approver_id,
                        "decision": r.decision.value,
                        "comment": r.comment,
                        "amount": r.amount,
                        "role_conflict": r.role_conflict,
                        "decided_at": r.decided_at,
                    }
                    for r in records
                ],
            )


# ---------------------------------------------------------------- buyurtma (PO)


def _order_row(order: PurchaseOrder) -> dict[str, Any]:
    return {
        "request_id": order.request_id,
        "supplier_id": order.supplier_id,
        "store_id": order.store_id,
        "delivery_date": order.delivery_date,
        "status": order.status.value,
        "total_amount": order.total,
        "confirmed_total": order.confirmed_total,
        "sent_at": order.sent_at,
        "sent_by": order.sent_by,
        "sent_channel": order.sent_channel.value if order.sent_channel else None,
        "response_deadline": order.response_deadline,
        "responded_at": order.responded_at,
        "cancel_reason": order.cancel_reason,
    }


def _order_lines(order: PurchaseOrder) -> list[dict[str, Any]]:
    return [
        {
            "id": line.id,
            "order_id": order.id,
            "position": position,
            "request_line_id": line.request_line_id,
            "product_id": line.product_id,
            "offer_id": line.offer_id,
            "pack_unit": line.pack_unit,
            "pack_factor": line.pack_factor,
            "qty_packs": line.qty_packs,
            "price_per_pack": line.price_per_pack,
            "response": line.response.value if line.response else None,
            "qty_confirmed": line.qty_confirmed,
            "price_confirmed": line.price_confirmed,
            "needs_reapproval": line.needs_reapproval,
        }
        for position, line in enumerate(order.lines)
    ]


class SqlOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def next_number(self) -> str:
        return f"PO-{await self._session.scalar(order_number_seq.next_value()):06d}"

    async def get(self, order_id: UUID) -> PurchaseOrder | None:
        row = (await self._session.execute(select(purchase_orders).where(purchase_orders.c.id == order_id))).first()
        if row is None:
            return None
        lines = await self._session.execute(
            select(purchase_order_lines)
            .where(purchase_order_lines.c.order_id == order_id)
            .order_by(purchase_order_lines.c.position)
        )
        return PurchaseOrder(
            id=row.id,
            number=row.number,
            request_id=row.request_id,
            supplier_id=row.supplier_id,
            store_id=row.store_id,
            delivery_date=row.delivery_date,
            status=OrderStatus(row.status),
            sent_at=row.sent_at,
            sent_by=row.sent_by,
            sent_channel=Channel(row.sent_channel) if row.sent_channel else None,
            response_deadline=row.response_deadline,
            responded_at=row.responded_at,
            cancel_reason=row.cancel_reason,
            version=row.version,
            lines=[
                OrderLine(
                    id=line.id,
                    request_line_id=line.request_line_id,
                    product_id=line.product_id,
                    offer_id=line.offer_id,
                    pack_unit=line.pack_unit,
                    pack_factor=line.pack_factor,
                    qty_packs=line.qty_packs,
                    price_per_pack=line.price_per_pack,
                    response=ResponseKind(line.response) if line.response else None,
                    qty_confirmed=line.qty_confirmed,
                    price_confirmed=line.price_confirmed,
                    needs_reapproval=line.needs_reapproval,
                )
                for line in lines
            ],
        )

    async def add(self, order: PurchaseOrder) -> None:
        await self._session.execute(
            insert(purchase_orders).values(id=order.id, number=order.number, version=order.version, **_order_row(order))
        )
        await _sync_lines(self._session, purchase_order_lines, "order_id", order.id, _order_lines(order))

    async def save(self, order: PurchaseOrder) -> None:
        await _bump(
            self._session, purchase_orders, order.id, order.version, values=_order_row(order), conflict="order.modified"
        )
        order.version += 1
        await _sync_lines(self._session, purchase_order_lines, "order_id", order.id, _order_lines(order))


# ---------------------------------------------------------------- yetkazuvchi havolasi


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class SqlResponseTokens:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def issue(self, order_id: UUID, *, expires_at: datetime) -> str:
        raw = secrets.token_urlsafe(24)
        await self._session.execute(
            insert(supplier_response_tokens).values(
                id=new_id(), order_id=order_id, token_hash=_hash(raw), expires_at=expires_at
            )
        )
        return raw

    async def resolve(self, raw_token: str, *, now: datetime) -> UUID | None:
        query = select(supplier_response_tokens.c.order_id).where(
            supplier_response_tokens.c.token_hash == _hash(raw_token), supplier_response_tokens.c.expires_at > now
        )
        order_id: UUID | None = await self._session.scalar(query)
        return order_id
