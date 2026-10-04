"""Yetkazuvchiga buyurtma (PurchaseOrder) — WORKFLOW B6, B7; ARCHITECTURE §5.

    CREATED → SENT → CONFIRMED | PARTIALLY_CONFIRMED          (keyingi bosqichlar: RECEIVING → RECEIVED → CLOSED)
               │  └─(narx dopuskdan tashqari)→ REAPPROVAL → CONFIRMED | PARTIALLY_CONFIRMED | CANCELLED
    CANCELLED (qabulgacha)

Bitta PO = bitta yetkazuvchi + bitta ombor + bitta yetkazish sanasi. Pozitsiyalar yetkazuvchi qadog'ida
(qop, quti) — narx va qadoq buyurtma paytida "muzlatiladi" (keyin prays o'zgarsa ham buyurtma o'zgarmaydi).
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import ClassVar, Self
from uuid import UUID

from zakup.shared_kernel.errors import DomainError, InvalidTransitionError, NotFoundError
from zakup.shared_kernel.events import AggregateRoot, DomainEvent
from zakup.shared_kernel.ids import new_id

MONEY_EXP = Decimal("0.01")
QTY_EXP = Decimal("0.0001")


class OrderStatus(StrEnum):
    CREATED = "CREATED"
    SENT = "SENT"
    CONFIRMED = "CONFIRMED"
    PARTIALLY_CONFIRMED = "PARTIALLY_CONFIRMED"
    REAPPROVAL = "REAPPROVAL"
    RECEIVED = "RECEIVED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    CANCELLED = "CANCELLED"


# Qabul qilish mumkin bo'lgan holatlar: javob kelmagan bo'lsa ham tovar kelishi mumkin
RECEIVABLE = frozenset({OrderStatus.SENT, OrderStatus.CONFIRMED, OrderStatus.PARTIALLY_CONFIRMED})


class Channel(StrEnum):
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    PHONE = "phone"
    EMAIL = "email"
    OTHER = "other"


class ResponseKind(StrEnum):
    CONFIRMED = "confirmed"
    PRICE_CHANGED = "price_changed"
    QTY_CHANGED = "qty_changed"
    OUT_OF_STOCK = "out_of_stock"


class InvalidOrderError(DomainError):
    code = "invalid_order"


@dataclass(frozen=True, slots=True)
class Tolerance:
    """Narx og'ishi: ±pct % va (berilgan bo'lsa) pozitsiya bo'yicha ko'pi bilan abs_max so'm (WORKFLOW B7)."""

    price_pct: Decimal = Decimal(3)
    abs_max: Decimal | None = None

    def accepts(self, *, ordered: Decimal, offered: Decimal, packs: Decimal) -> bool:
        if ordered == 0:
            return offered == 0
        delta = abs(offered - ordered)
        if delta / ordered * 100 > self.price_pct:
            return False
        return self.abs_max is None or delta * packs <= self.abs_max


@dataclass(frozen=True, slots=True)
class LineResponse:
    kind: ResponseKind
    qty_packs: Decimal | None = None  # QTY_CHANGED
    price_per_pack: Decimal | None = None  # PRICE_CHANGED


@dataclass(slots=True)
class OrderLine:
    id: UUID
    request_line_id: UUID | None
    product_id: UUID
    offer_id: UUID
    pack_unit: str
    pack_factor: Decimal
    qty_packs: Decimal
    price_per_pack: Decimal
    response: ResponseKind | None = None
    qty_confirmed: Decimal | None = None
    price_confirmed: Decimal | None = None
    needs_reapproval: bool = False

    @property
    def qty_base(self) -> Decimal:
        return (self.qty_packs * self.pack_factor).quantize(QTY_EXP, ROUND_HALF_UP)

    @property
    def amount(self) -> Decimal:
        return (self.qty_packs * self.price_per_pack).quantize(MONEY_EXP, ROUND_HALF_UP)

    @property
    def confirmed_amount(self) -> Decimal:
        if self.response is None:
            return self.amount
        qty = self.qty_confirmed if self.qty_confirmed is not None else self.qty_packs
        price = self.price_confirmed if self.price_confirmed is not None else self.price_per_pack
        return (qty * price).quantize(MONEY_EXP, ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class NewOrderLine:
    request_line_id: UUID | None
    product_id: UUID
    offer_id: UUID
    pack_unit: str
    pack_factor: Decimal
    qty_packs: Decimal
    price_per_pack: Decimal


@dataclass(frozen=True, kw_only=True)
class OrderSent(DomainEvent):
    event_type: ClassVar[str] = "procurement.order_sent"
    supplier_id: str
    channel: str


@dataclass(frozen=True, kw_only=True)
class OrderResponded(DomainEvent):
    event_type: ClassVar[str] = "procurement.order_responded"
    status: str


class PurchaseOrder(AggregateRoot):
    aggregate_type: ClassVar[str] = "procurement.purchase_order"

    def __init__(
        self,
        *,
        id: UUID,  # noqa: A002
        number: str,
        request_id: UUID | None,
        supplier_id: UUID,
        store_id: UUID,
        delivery_date: date,
        status: OrderStatus,
        lines: list[OrderLine],
        sent_at: datetime | None = None,
        sent_by: UUID | None = None,
        sent_channel: Channel | None = None,
        response_deadline: datetime | None = None,
        responded_at: datetime | None = None,
        cancel_reason: str | None = None,
        version: int = 1,
    ) -> None:
        super().__init__()
        self.id = id
        self.number = number
        self.request_id = request_id
        self.supplier_id = supplier_id
        self.store_id = store_id
        self.delivery_date = delivery_date
        self.status = status
        self.lines = lines
        self.sent_at = sent_at
        self.sent_by = sent_by
        self.sent_channel = sent_channel
        self.response_deadline = response_deadline
        self.responded_at = responded_at
        self.cancel_reason = cancel_reason
        self.version = version

    @classmethod
    def create(
        cls,
        *,
        number: str,
        request_id: UUID | None,
        supplier_id: UUID,
        store_id: UUID,
        delivery_date: date,
        lines: list[NewOrderLine],
    ) -> Self:
        if not lines:
            raise InvalidOrderError("order.empty")
        return cls(
            id=new_id(),
            number=number,
            request_id=request_id,
            supplier_id=supplier_id,
            store_id=store_id,
            delivery_date=delivery_date,
            status=OrderStatus.CREATED,
            lines=[
                OrderLine(
                    id=new_id(),
                    request_line_id=line.request_line_id,
                    product_id=line.product_id,
                    offer_id=line.offer_id,
                    pack_unit=line.pack_unit,
                    pack_factor=line.pack_factor,
                    qty_packs=line.qty_packs,
                    price_per_pack=line.price_per_pack,
                )
                for line in lines
            ],
        )

    @property
    def total(self) -> Decimal:
        return sum((line.amount for line in self.lines), Decimal(0))

    @property
    def confirmed_total(self) -> Decimal:
        return sum((line.confirmed_amount for line in self.lines), Decimal(0))

    def send(self, *, by: UUID, channel: Channel, at: datetime, deadline: datetime) -> None:
        """Yuborilgan payt — tovar "yo'lda" hisoblana boshlaydi (WORKFLOW B6.5). Qayta yuborish — kanal yangilanadi."""
        self._require(OrderStatus.CREATED, OrderStatus.SENT)
        if self.status is OrderStatus.CREATED:
            self.sent_at = at
        self.sent_by = by
        self.sent_channel = channel
        self.response_deadline = deadline
        self.status = OrderStatus.SENT
        self.record(OrderSent(aggregate_id=self.id, supplier_id=str(self.supplier_id), channel=channel.value))

    def record_response(self, responses: dict[UUID, LineResponse], tolerance: Tolerance, *, at: datetime) -> None:
        """Javob — har pozitsiya bo'yicha; javobsiz pozitsiya "tasdiqlangan" deb olinadi."""
        self._require(OrderStatus.SENT)
        unknown = set(responses) - {line.id for line in self.lines}
        if unknown:
            raise NotFoundError("order.line_not_found")
        for line in self.lines:
            _apply(line, responses.get(line.id, LineResponse(ResponseKind.CONFIRMED)), tolerance)
        self.responded_at = at
        self.status = self._status_after_response()
        self.record(OrderResponded(aggregate_id=self.id, status=self.status.value))

    def approve_changes(self) -> None:
        """Dopuskdan tashqari narx tasdiqlovchi tomonidan qabul qilindi."""
        self._require(OrderStatus.REAPPROVAL)
        for line in self.lines:
            line.needs_reapproval = False
        self.status = self._status_after_response()

    def mark_received(self, *, complete: bool) -> None:
        """Qabul yakunlandi (receiving moduli chaqiradi). Bitta buyurtma — bitta qabul (MVP)."""
        if self.status not in RECEIVABLE:
            raise InvalidTransitionError("order.invalid_status", status=self.status.value)
        self.status = OrderStatus.RECEIVED if complete else OrderStatus.PARTIALLY_RECEIVED

    @property
    def expected_lines(self) -> list[tuple[OrderLine, Decimal, Decimal]]:
        """(pozitsiya, kutilgan bazaviy miqdor, bazaviy birlik narxi) — yetkazuvchi javobi hisobga olingan."""
        result = []
        for line in self.lines:
            packs = line.qty_confirmed if line.qty_confirmed is not None else line.qty_packs
            price = line.price_confirmed if line.price_confirmed is not None else line.price_per_pack
            if packs > 0:
                result.append(
                    (
                        line,
                        (packs * line.pack_factor).quantize(QTY_EXP, ROUND_HALF_UP),
                        (price / line.pack_factor).quantize(QTY_EXP, ROUND_HALF_UP),
                    )
                )
        return result

    def cancel(self, *, reason: str) -> None:
        self._require(OrderStatus.CREATED, OrderStatus.SENT, OrderStatus.REAPPROVAL)
        cleaned = " ".join(reason.split())[:500]
        if not cleaned:
            raise InvalidOrderError("order.reason_required")
        self.cancel_reason = cleaned
        self.status = OrderStatus.CANCELLED

    def _status_after_response(self) -> OrderStatus:
        if any(line.needs_reapproval for line in self.lines):
            return OrderStatus.REAPPROVAL
        if all(line.response is ResponseKind.OUT_OF_STOCK for line in self.lines):
            return OrderStatus.CANCELLED
        shortfall = any(
            line.response is ResponseKind.OUT_OF_STOCK
            or (line.qty_confirmed is not None and line.qty_confirmed < line.qty_packs)
            for line in self.lines
        )
        return OrderStatus.PARTIALLY_CONFIRMED if shortfall else OrderStatus.CONFIRMED

    def _require(self, *allowed: OrderStatus) -> None:
        if self.status not in allowed:
            raise InvalidTransitionError("order.invalid_status", status=self.status.value)


def _apply(line: OrderLine, response: LineResponse, tolerance: Tolerance) -> None:
    line.response = response.kind
    line.qty_confirmed = line.qty_packs
    line.price_confirmed = line.price_per_pack
    line.needs_reapproval = False
    match response.kind:
        case ResponseKind.OUT_OF_STOCK:
            line.qty_confirmed = Decimal(0)
        case ResponseKind.QTY_CHANGED:
            if response.qty_packs is None or response.qty_packs < 0:
                raise InvalidOrderError("order.qty_required")
            line.qty_confirmed = response.qty_packs
        case ResponseKind.PRICE_CHANGED:
            if response.price_per_pack is None or response.price_per_pack < 0:
                raise InvalidOrderError("order.price_required")
            line.price_confirmed = response.price_per_pack
            line.needs_reapproval = not tolerance.accepts(
                ordered=line.price_per_pack, offered=response.price_per_pack, packs=line.qty_packs
            )
        case ResponseKind.CONFIRMED:
            pass
