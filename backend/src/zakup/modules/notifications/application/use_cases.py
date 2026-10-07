"""Bildirishnomalar (WORKFLOW: bot xabarlari): outbox event → kimga, qanday matn → navbat → Telegram.

Ikki bosqich: `NotifyOnEvent` xabarlarni navbatga yozadi (outbox handler, idempotent), `SendNextMessage`
ularni bittadan yuboradi (worker). Shunda Telegram xatosi faqat o'sha xabarni qayta yuboradi, eventni emas.
"""

from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, ClassVar
from uuid import UUID, uuid5

import structlog

from zakup.modules.notifications.application.ports import (
    DeliveryRefusedError,
    Directory,
    MessageQueue,
    OutgoingMessage,
    Recipient,
    Sender,
)
from zakup.modules.notifications.domain.messages import BUTTON, Facts, Kind, render

log = structlog.get_logger()

DECIDERS = ("buyer", "approver", "admin")
MANAGERS = frozenset({"buyer", "admin"})
APPROVERS = frozenset({"approver", "admin"})
PAYERS = frozenset({"accountant", "admin"})
ADMINS = frozenset({"admin"})
STOREKEEPERS = frozenset({"storekeeper"})
DECISION_KIND = {
    "approved": Kind.REQUEST_APPROVED,
    "partial": Kind.REQUEST_PARTIAL,
    "returned": Kind.REQUEST_RETURNED,
    "rejected": Kind.REQUEST_REJECTED,
}
MAX_ATTEMPTS = 6
TASHKENT = timedelta(hours=5)

Rule = Callable[[UUID, dict[str, Any]], Awaitable[list[OutgoingMessage]]]


class NotifyOnEvent:
    """Event → xabarlar navbati. Muallif o'zi qilgan ish haqida xabar olmaydi."""

    def __init__(
        self, directory: Directory, queue: MessageQueue, approval_limits: Mapping[str, Decimal | None]
    ) -> None:
        self._dir = directory
        self._queue = queue
        self._limits = approval_limits

    # event → qoida (metod nomi)
    RULES: ClassVar[dict[str, str]] = {
        "procurement.request_submitted": "_request_submitted",
        "procurement.request_decided": "_request_decided",
        "procurement.auto_request_drafted": "_auto_drafted",
        "procurement.order_responded": "_order_responded",
        "procurement.order_changes_approved": "_order_changes_approved",
        "receiving.receipt_disputed": "_receipt_disputed",
        "finance.payment_submitted": "_payment_submitted",
        "finance.payment_approved": "_payment_approved",
        "finance.payment_rejected": "_payment_rejected",
        "finance.payment_paid": "_payment_paid",
        "identity.user_signed_up": "_user_signed_up",
        "identity.user_activated": "_user_activated",
    }

    async def __call__(self, event_type: str, payload: dict[str, Any]) -> int:
        name = self.RULES.get(event_type)
        if name is None:
            return 0
        rule: Rule = getattr(self, name)
        messages = await rule(UUID(payload["event_id"]), payload)
        await self._queue.enqueue(messages)
        return len(messages)

    # ------------------------------------------------------------ yordamchilar

    @staticmethod
    def _build(
        key: UUID, recipients: list[Recipient], kind: Kind, facts: Facts, path: str | None, *, skip: set[UUID]
    ) -> list[OutgoingMessage]:
        seen: set[UUID] = set()
        out = []
        for r in recipients:
            if r.user_id in skip or r.user_id in seen:
                continue
            seen.add(r.user_id)
            out.append(OutgoingMessage(key=key, recipient=r, text=render(kind, r.locale, facts), path=path))
        return out

    def _deciders_for(self, amount: Decimal) -> frozenset[str]:
        """Limit yetadigan rollar (limit None — cheklanmagan)."""
        return frozenset(
            role
            for role in DECIDERS
            if role in self._limits and (self._limits[role] is None or self._limits[role] >= amount)  # type: ignore[operator]
        )

    async def _one(self, user_id: UUID | None) -> list[Recipient]:
        if user_id is None:
            return []
        r = await self._dir.user(user_id)
        return [r] if r else []

    # ------------------------------------------------------------ qoidalar

    async def _request_submitted(self, key: UUID, p: dict[str, Any]) -> list[OutgoingMessage]:
        req = await self._dir.request(UUID(p["aggregate_id"]))
        if req is None:
            return []
        to = await self._dir.with_roles(self._deciders_for(req.amount) or ADMINS, req.store_id)
        facts = Facts(number=req.number, store=req.store, amount=str(req.amount), day=req.needed_by)
        return self._build(
            key, to, Kind.REQUEST_PENDING, facts, f"/requests/{p['aggregate_id']}", skip={req.initiator_id}
        )

    async def _request_decided(self, key: UUID, p: dict[str, Any]) -> list[OutgoingMessage]:
        kind = DECISION_KIND.get(p.get("decision", ""))
        req = await self._dir.request(UUID(p["aggregate_id"]))
        if kind is None or req is None:
            return []
        facts = Facts(number=req.number, store=req.store, comment=req.last_comment or "")
        skip = {UUID(p["approver_id"])}
        return self._build(
            key, await self._one(req.initiator_id), kind, facts, f"/requests/{p['aggregate_id']}", skip=skip
        )

    async def _auto_drafted(self, key: UUID, p: dict[str, Any]) -> list[OutgoingMessage]:
        req = await self._dir.request(UUID(p["aggregate_id"]))
        if req is None:
            return []
        to = await self._dir.with_roles(MANAGERS, req.store_id)
        facts = Facts(number=req.number, store=req.store, amount=str(req.amount), lines=req.lines)
        return self._build(key, to, Kind.AUTO_DRAFT, facts, f"/requests/{p['aggregate_id']}", skip=set())

    async def _order_responded(self, key: UUID, p: dict[str, Any]) -> list[OutgoingMessage]:
        order = await self._dir.order(UUID(p["aggregate_id"]))
        if order is None:
            return []
        path = f"/orders/{p['aggregate_id']}"
        facts = Facts(
            number=order.number,
            store=order.store,
            supplier=order.supplier,
            amount=str(order.amount),
            day=order.delivery_date,
        )
        status = p.get("status")
        if status == "REAPPROVAL":
            to = await self._dir.with_roles(APPROVERS, order.store_id)
            return self._build(key, to, Kind.ORDER_REAPPROVAL, facts, path, skip=set())
        if status in ("CONFIRMED", "PARTIALLY_CONFIRMED"):
            # Buyurtmani yuborgan zakupshik; u yo'q bo'lsa — ombordagi zakupshiklar
            to = await self._one(order.sent_by) or await self._dir.with_roles(MANAGERS, order.store_id)
            return self._build(key, to, Kind.ORDER_CONFIRMED, facts, path, skip=set())
        return []

    async def _order_changes_approved(self, key: UUID, p: dict[str, Any]) -> list[OutgoingMessage]:
        order = await self._dir.order(UUID(p["aggregate_id"]))
        if order is None:
            return []
        facts = Facts(number=order.number, store=order.store, supplier=order.supplier, amount=str(order.amount))
        to = await self._one(order.sent_by) or await self._dir.with_roles(MANAGERS, order.store_id)
        return self._build(key, to, Kind.ORDER_CHANGES_APPROVED, facts, f"/orders/{p['aggregate_id']}", skip=set())

    async def _receipt_disputed(self, key: UUID, p: dict[str, Any]) -> list[OutgoingMessage]:
        receipt = await self._dir.receipt(UUID(p["aggregate_id"]))
        if receipt is None:
            return []
        to = await self._dir.with_roles(MANAGERS | APPROVERS, receipt.store_id)
        facts = Facts(number=receipt.number, store=receipt.store, supplier=receipt.supplier, amount=str(receipt.amount))
        path = f"/receiving/receipts/{p['aggregate_id']}"
        return self._build(key, to, Kind.RECEIPT_DISPUTED, facts, path, skip={receipt.received_by})

    async def _payment_submitted(self, key: UUID, p: dict[str, Any]) -> list[OutgoingMessage]:
        payment = await self._dir.payment(UUID(p["aggregate_id"]))
        if payment is None:
            return []
        # Tasdiq shart bo'lmasa zayavka darhol APPROVED — to'g'ridan-to'g'ri buxgalterga
        kind, roles = (
            (Kind.PAYMENT_TO_APPROVE, APPROVERS) if p.get("status") == "SUBMITTED" else (Kind.PAYMENT_TO_PAY, PAYERS)
        )
        facts = Facts(number=payment.number, supplier=payment.supplier, amount=str(payment.amount))
        to = await self._dir.with_roles(roles, None)
        return self._build(key, to, kind, facts, f"/finance/payments/{p['aggregate_id']}", skip={payment.requested_by})

    async def _payment_approved(self, key: UUID, p: dict[str, Any]) -> list[OutgoingMessage]:
        payment = await self._dir.payment(UUID(p["aggregate_id"]))
        if payment is None:
            return []
        facts = Facts(number=payment.number, supplier=payment.supplier, amount=str(payment.amount))
        to = await self._dir.with_roles(PAYERS, None)
        skip = {payment.approved_by} if payment.approved_by else set()
        return self._build(key, to, Kind.PAYMENT_TO_PAY, facts, f"/finance/payments/{p['aggregate_id']}", skip=skip)

    async def _payment_rejected(self, key: UUID, p: dict[str, Any]) -> list[OutgoingMessage]:
        payment = await self._dir.payment(UUID(p["aggregate_id"]))
        if payment is None:
            return []
        facts = Facts(number=payment.number, supplier=payment.supplier, comment=p.get("comment", ""))
        skip = {payment.approved_by} if payment.approved_by else set()
        path = f"/finance/payments/{p['aggregate_id']}"
        return self._build(key, await self._one(payment.requested_by), Kind.PAYMENT_REJECTED, facts, path, skip=skip)

    async def _payment_paid(self, key: UUID, p: dict[str, Any]) -> list[OutgoingMessage]:
        payment = await self._dir.payment(UUID(p["aggregate_id"]))
        if payment is None:
            return []
        facts = Facts(number=payment.number, supplier=payment.supplier, amount=str(payment.amount))
        path = f"/finance/payments/{p['aggregate_id']}"
        return self._build(key, await self._one(payment.requested_by), Kind.PAYMENT_PAID, facts, path, skip=set())

    async def _user_signed_up(self, key: UUID, p: dict[str, Any]) -> list[OutgoingMessage]:
        user_id = UUID(p["aggregate_id"])
        info = await self._dir.user_info(user_id)
        if info is None or info.is_active:  # bootstrap admin darhol faol — xabar shart emas
            return []
        to = await self._dir.with_roles(ADMINS, None)
        facts = Facts(name=info.full_name, telegram_id=info.telegram_id)
        return self._build(key, to, Kind.USER_PENDING, facts, f"/admin/users/{user_id}", skip={user_id})

    async def _user_activated(self, key: UUID, p: dict[str, Any]) -> list[OutgoingMessage]:
        by = p.get("by")
        if not by:  # bootstrap admin birinchi kirishda — u allaqachon ilovada
            return []
        to = await self._one(UUID(p["aggregate_id"]))
        return self._build(key, to, Kind.USER_ACTIVATED, Facts(), "/", skip={UUID(by)})


class DeliveriesDigest:
    """Ertalab omborchiga: bugun qaysi yetkazuvchilar keladi (kunlik ish)."""

    def __init__(self, directory: Directory, queue: MessageQueue, clock: Callable[[], datetime]) -> None:
        self._dir = directory
        self._queue = queue
        self._clock = clock

    async def __call__(self) -> int:
        today: date = (self._clock() + TASHKENT).date()
        messages: list[OutgoingMessage] = []
        for store in await self._dir.deliveries(today):
            facts = Facts(store=store.store, lines=len(store.suppliers), items=tuple(store.suppliers))
            key = uuid5(store.store_id, f"deliveries:{today.isoformat()}")
            to = await self._dir.with_roles(STOREKEEPERS, store.store_id)
            messages += NotifyOnEvent._build(key, to, Kind.DELIVERIES_TODAY, facts, "/receiving", skip=set())
        await self._queue.enqueue(messages)
        return len(messages)


class SendNextMessage:
    """Navbatdan bitta xabar → Telegram. Vaqtinchalik xato — kechikish bilan qayta, qat'iy rad — to'xtatiladi."""

    def __init__(
        self,
        queue: MessageQueue,
        sender: Sender,
        public_base_url: str,
        commit: Callable[[], Awaitable[None]],
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._queue = queue
        self._sender = sender
        self._base = public_base_url.rstrip("/")
        self._commit = commit
        self._clock = clock

    async def __call__(self) -> bool:
        now = self._clock()
        message = await self._queue.next_pending(now)
        if message is None:
            return False
        await self._commit()  # ijara saqlansin; Telegram so'rovi tranzaksiyadan tashqarida
        # Telegram web_app tugmasi faqat https bilan ishlaydi (local'da tugmasiz)
        button = (
            (BUTTON.get(message.locale, BUTTON["ru"]), self._base + message.path)
            if message.path is not None and self._base.startswith("https://")
            else None
        )
        try:
            await self._sender.send(message.chat_id, message.text, button)
        except DeliveryRefusedError as exc:
            await self._queue.mark_failed(message.id, str(exc)[:500])
            log.info("notification_refused", message_id=str(message.id), error=str(exc))
        except Exception as exc:
            attempts = message.attempts + 1
            if attempts >= MAX_ATTEMPTS:
                await self._queue.mark_failed(message.id, str(exc)[:500])
            else:
                delay = timedelta(seconds=30 * 2**message.attempts)
                await self._queue.mark_retry(message.id, str(exc)[:500], now + delay)
            log.warning("notification_failed", message_id=str(message.id), error=str(exc))
        else:
            await self._queue.mark_sent(message.id, now)
        await self._commit()
        return True
