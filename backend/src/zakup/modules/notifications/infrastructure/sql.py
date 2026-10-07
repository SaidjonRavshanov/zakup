"""notifications: boshqa modullar ma'lumotini read-only SQL bilan o'qiydi (analytics kabi — kod importisiz)
va o'z navbatini (notify.messages) yuritadi."""

from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from zakup.modules.notifications.application.ports import (
    OrderInfo,
    OutgoingMessage,
    PaymentInfo,
    PendingMessage,
    ReceiptInfo,
    Recipient,
    RequestInfo,
    StoreDeliveries,
    UserInfo,
)
from zakup.modules.notifications.infrastructure.tables import messages
from zakup.shared_kernel.ids import uuid7

LEASE = timedelta(minutes=5)
_RECIPIENT = "SELECT DISTINCT u.id, u.telegram_id, u.locale FROM identity.users u"


def _recipient(row: Any) -> Recipient:
    return Recipient(user_id=row.id, telegram_id=row.telegram_id, locale=row.locale)


class SqlDirectory:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def _one(self, sql: str, **params: Any) -> Any:
        return (await self._s.execute(text(sql), params)).first()

    async def with_roles(self, roles: frozenset[str], store_id: UUID | None) -> list[Recipient]:
        rows = await self._s.execute(
            text(
                f"""{_RECIPIENT}
                JOIN identity.user_roles g ON g.user_id = u.id
                WHERE u.is_active AND u.telegram_id > 0 AND g.role = ANY(:roles)
                  AND (CAST(:store AS uuid) IS NULL OR g.store_id IS NULL OR g.store_id = :store)"""
            ),
            {"roles": sorted(roles), "store": store_id},
        )
        return [_recipient(r) for r in rows]

    async def user(self, user_id: UUID) -> Recipient | None:
        row = await self._one(f"{_RECIPIENT} WHERE u.id = :id AND u.is_active AND u.telegram_id > 0", id=user_id)
        return _recipient(row) if row else None

    async def user_info(self, user_id: UUID) -> UserInfo | None:
        row = await self._one("SELECT full_name, telegram_id, is_active FROM identity.users WHERE id = :id", id=user_id)
        return UserInfo(row.full_name, row.telegram_id, row.is_active) if row else None

    async def request(self, request_id: UUID) -> RequestInfo | None:
        row = await self._one(
            """SELECT r.number, r.store_id, s.name AS store, r.total_amount, r.needed_by, r.initiator_id,
                      (SELECT count(*) FROM procurement.purchase_request_lines l WHERE l.request_id = r.id) AS lines,
                      (SELECT a.comment FROM procurement.approvals a WHERE a.request_id = r.id
                        ORDER BY a.decided_at DESC LIMIT 1) AS last_comment
               FROM procurement.purchase_requests r JOIN catalog.stores s ON s.id = r.store_id
               WHERE r.id = :id""",
            id=request_id,
        )
        if row is None:
            return None
        return RequestInfo(
            row.number,
            row.store_id,
            row.store,
            row.total_amount,
            row.needed_by,
            row.initiator_id,
            row.lines,
            row.last_comment,
        )

    async def order(self, order_id: UUID) -> OrderInfo | None:
        row = await self._one(
            """SELECT o.number, o.store_id, st.name AS store, su.name AS supplier, o.delivery_date,
                      COALESCE(NULLIF(o.confirmed_total, 0), o.total_amount) AS amount, o.sent_by
               FROM procurement.purchase_orders o
               JOIN catalog.stores st ON st.id = o.store_id JOIN catalog.suppliers su ON su.id = o.supplier_id
               WHERE o.id = :id""",
            id=order_id,
        )
        if row is None:
            return None
        return OrderInfo(row.number, row.store_id, row.store, row.supplier, row.delivery_date, row.amount, row.sent_by)

    async def receipt(self, receipt_id: UUID) -> ReceiptInfo | None:
        row = await self._one(
            """SELECT r.number, r.store_id, st.name AS store, su.name AS supplier, r.total, r.received_by
               FROM receiving.receipts r
               JOIN catalog.stores st ON st.id = r.store_id JOIN catalog.suppliers su ON su.id = r.supplier_id
               WHERE r.id = :id""",
            id=receipt_id,
        )
        if row is None:
            return None
        return ReceiptInfo(row.number, row.store_id, row.store, row.supplier, row.total, row.received_by)

    async def payment(self, payment_id: UUID) -> PaymentInfo | None:
        row = await self._one(
            """SELECT p.number, su.name AS supplier, p.total, p.requested_by, p.approved_by, p.decision_comment
               FROM finance.payment_requests p JOIN catalog.suppliers su ON su.id = p.supplier_id
               WHERE p.id = :id""",
            id=payment_id,
        )
        if row is None:
            return None
        return PaymentInfo(row.number, row.supplier, row.total, row.requested_by, row.approved_by, row.decision_comment)

    async def deliveries(self, day: date) -> list[StoreDeliveries]:
        rows = await self._s.execute(
            text(
                """SELECT o.store_id, st.name AS store, array_agg(DISTINCT su.name) AS suppliers
                   FROM procurement.purchase_orders o
                   JOIN catalog.stores st ON st.id = o.store_id JOIN catalog.suppliers su ON su.id = o.supplier_id
                   WHERE o.delivery_date = :day AND o.status IN ('SENT', 'CONFIRMED', 'PARTIALLY_CONFIRMED')
                   GROUP BY o.store_id, st.name"""
            ),
            {"day": day},
        )
        return [StoreDeliveries(r.store_id, r.store, sorted(r.suppliers)) for r in rows]


class SqlMessageQueue:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def enqueue(self, outgoing: list[OutgoingMessage]) -> None:
        if not outgoing:
            return
        await self._s.execute(
            insert(messages)
            .values(
                [
                    {
                        "id": uuid7(),
                        "key": m.key,
                        "user_id": m.recipient.user_id,
                        "chat_id": m.recipient.telegram_id,
                        "locale": m.recipient.locale,
                        "text": m.text,
                        "path": m.path,
                    }
                    for m in outgoing
                ]
            )
            .on_conflict_do_nothing(index_elements=["key", "user_id"])
        )

    async def next_pending(self, now: datetime) -> PendingMessage | None:
        """Navbatdagi xabarni "ijaraga" oladi: next_attempt_at = now + LEASE (chaqiruvchi darhol commit qiladi).

        Telegram'ga so'rov tranzaksiyadan tashqarida — ulanish band turmaydi; jarayon yiqilsa xabar ijara
        tugagach qayta olinadi.
        """
        claimable = (
            select(messages.c.id)
            .where(messages.c.status == "pending", messages.c.next_attempt_at <= now)
            .order_by(messages.c.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )
        row = (
            await self._s.execute(
                update(messages)
                .where(messages.c.id == claimable)
                .values(next_attempt_at=now + LEASE)
                .returning(
                    messages.c.id,
                    messages.c.chat_id,
                    messages.c.text,
                    messages.c.path,
                    messages.c.locale,
                    messages.c.attempts,
                )
            )
        ).first()
        if row is None:
            return None
        return PendingMessage(row.id, row.chat_id, row.text, row.path, row.locale, row.attempts)

    async def mark_sent(self, message_id: UUID, at: datetime) -> None:
        await self._s.execute(update(messages).where(messages.c.id == message_id).values(status="sent", sent_at=at))

    async def mark_retry(self, message_id: UUID, error: str, next_attempt_at: datetime) -> None:
        await self._s.execute(
            update(messages)
            .where(messages.c.id == message_id)
            .values(attempts=messages.c.attempts + 1, last_error=error, next_attempt_at=next_attempt_at)
        )

    async def mark_failed(self, message_id: UUID, error: str) -> None:
        await self._s.execute(
            update(messages)
            .where(messages.c.id == message_id)
            .values(status="failed", attempts=messages.c.attempts + 1, last_error=error)
        )
