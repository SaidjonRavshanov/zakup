"""Qabul (Receipt) — WORKFLOW B8, B9; ARCHITECTURE §5.

    (oflayn yig'iladi) → submit → ACCEPTED                       → iiko'ga kirim (integration_iiko)
                               └→ DISPUTED → nizo yechildi → ACCEPTED

Miqdor — tovarning **bazaviy birligida** (kg, dona): omborchi tortadi / sanaydi, iiko kirimi ham shu birlikda.
Narx — bazaviy birlik uchun (yetkazuvchi nakladnoyidan). ID — klientda yaratiladi (UUIDv7, oflayn, ADR-08/10):
qayta yuborish dublikat yaratmaydi.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import ClassVar, Self
from uuid import UUID

from zakup.shared_kernel.errors import DomainError, InvalidTransitionError
from zakup.shared_kernel.events import AggregateRoot, DomainEvent

MONEY = Decimal("0.01")
QTY = Decimal("0.0001")
WEIGHT_UNITS = frozenset({"kg", "g", "l", "ml"})
MAX_TEXT = 500


class ReceiptStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    DISPUTED = "DISPUTED"


class PaymentMethod(StrEnum):
    CASH = "cash"
    TRANSFER = "transfer"


class DiscrepancyKind(StrEnum):
    QTY_OVER = "qty_over"
    QTY_UNDER = "qty_under"
    SHORT = "short"  # umuman kelmadi (недовоз)
    PRICE_UP = "price_up"
    PRICE_DOWN = "price_down"  # tejash — hech qachon bloklamaydi
    DEFECT = "defect"


class Resolution(StrEnum):
    ACCEPTED = "accepted"  # fakt bo'yicha qabul
    RETURN = "return"  # brak / ortiqcha — qaytariladi
    DISCOUNT = "discount"  # chegirma (moliya bosqichida summa kamayadi)
    REPLACEMENT = "replacement"  # almashtirib beriladi


class InvalidReceiptError(DomainError):
    code = "invalid_receipt"


@dataclass(frozen=True, slots=True)
class ReceivingTolerance:
    """Dopusklar (WORKFLOW B9): vaznli tovar — %, donali — aniq; narx oshishi — %."""

    qty_weight_pct: Decimal = Decimal(3)
    qty_piece_pct: Decimal = Decimal(0)
    price_pct: Decimal = Decimal(3)

    def qty_pct(self, base_unit: str) -> Decimal:
        return self.qty_weight_pct if base_unit in WEIGHT_UNITS else self.qty_piece_pct


@dataclass(frozen=True, slots=True)
class ExpectedLine:
    """Buyurtmadan kutilgan: tasdiqlangan miqdor / narx (yetkazuvchi javobi bo'lsa — o'sha)."""

    order_line_id: UUID
    product_id: UUID
    base_unit: str
    qty: Decimal
    price: Decimal


@dataclass(frozen=True, slots=True)
class FactLine:
    order_line_id: UUID
    qty: Decimal
    price: Decimal
    qty_defect: Decimal = Decimal(0)
    defect_reason: str | None = None


@dataclass(slots=True)
class ReceiptLine:
    id: UUID
    order_line_id: UUID
    product_id: UUID
    base_unit: str
    qty_expected: Decimal
    price_expected: Decimal
    qty_fact: Decimal
    price_fact: Decimal
    qty_defect: Decimal = Decimal(0)
    defect_reason: str | None = None

    @property
    def qty_accepted(self) -> Decimal:
        """Kirim qilinadigan miqdor: brak qabul qilinmaydi (qaytarishga ketadi)."""
        return max(self.qty_fact - self.qty_defect, Decimal(0))

    @property
    def amount(self) -> Decimal:
        return (self.qty_accepted * self.price_fact).quantize(MONEY, ROUND_HALF_UP)

    @property
    def expected_amount(self) -> Decimal:
        return (self.qty_expected * self.price_expected).quantize(MONEY, ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class Discrepancy:
    line_id: UUID
    kind: DiscrepancyKind
    expected: Decimal
    actual: Decimal
    within_tolerance: bool

    @property
    def blocking(self) -> bool:
        return not self.within_tolerance and self.kind is not DiscrepancyKind.PRICE_DOWN


@dataclass(slots=True)
class Dispute:
    opened_at: datetime
    resolution: Resolution | None = None
    comment: str | None = None
    resolved_by: UUID | None = None
    resolved_at: datetime | None = None

    @property
    def is_open(self) -> bool:
        return self.resolution is None


@dataclass(frozen=True, kw_only=True)
class ReceiptAccepted(DomainEvent):
    """Qabul yakunlandi (bloklovchi farq yo'q yoki nizo yechildi) → iiko kirimi, majburiyat, akt."""

    event_type: ClassVar[str] = "receiving.receipt_accepted"
    number: str
    order_id: str
    store_id: str
    supplier_id: str
    amount: str
    received_at: str
    had_dispute: bool


@dataclass(frozen=True, kw_only=True)
class ReceiptDisputed(DomainEvent):
    """Nizo ochildi → majburiyat bloklangan holda yaratiladi (to'lab bo'lmaydi)."""

    event_type: ClassVar[str] = "receiving.receipt_disputed"
    number: str
    order_id: str
    store_id: str
    supplier_id: str
    amount: str
    received_at: str
    kinds: list[str]


@dataclass(kw_only=True)
class ReceiptHeader:
    order_id: UUID
    store_id: UUID
    supplier_id: UUID
    received_by: UUID
    received_at: datetime
    supplier_invoice_no: str | None
    payment_method: PaymentMethod | None
    invoice_photo_id: UUID
    comment: str | None = None


class Receipt(AggregateRoot):
    aggregate_type: ClassVar[str] = "receiving.receipt"

    def __init__(
        self,
        *,
        id: UUID,  # noqa: A002
        number: str,
        header: ReceiptHeader,
        status: ReceiptStatus,
        lines: list[ReceiptLine],
        discrepancies: list[Discrepancy],
        dispute: Dispute | None = None,
        version: int = 1,
    ) -> None:
        super().__init__()
        self.id = id
        self.number = number
        self.header = header
        self.status = status
        self.lines = lines
        self.discrepancies = discrepancies
        self.dispute = dispute
        self.version = version

    @classmethod
    def submit(
        cls,
        *,
        id: UUID,  # noqa: A002 — klient yaratgan (oflayn)
        number: str,
        header: ReceiptHeader,
        expected: list[ExpectedLine],
        facts: list[FactLine],
        line_ids: list[UUID],
        tolerance: ReceivingTolerance,
    ) -> Self:
        by_line = {fact.order_line_id: fact for fact in facts}
        if set(by_line) - {e.order_line_id for e in expected} or len(by_line) != len(facts):
            raise InvalidReceiptError("receipt.unknown_line")
        lines = [
            _line(line_id, item, by_line.get(item.order_line_id))
            for line_id, item in zip(line_ids, expected, strict=True)
        ]
        header.supplier_invoice_no = _clean(header.supplier_invoice_no)
        header.comment = _clean(header.comment)
        discrepancies = [d for line in lines for d in _discrepancies(line, tolerance)]
        blocking = [d for d in discrepancies if d.blocking]
        receipt = cls(
            id=id,
            number=number,
            header=header,
            status=ReceiptStatus.DISPUTED if blocking else ReceiptStatus.ACCEPTED,
            lines=lines,
            discrepancies=discrepancies,
            dispute=Dispute(opened_at=header.received_at) if blocking else None,
        )
        if blocking:
            receipt.record(
                ReceiptDisputed(
                    aggregate_id=receipt.id,
                    number=receipt.number,
                    order_id=str(header.order_id),
                    store_id=str(header.store_id),
                    supplier_id=str(header.supplier_id),
                    amount=str(receipt.total),
                    received_at=header.received_at.isoformat(),
                    kinds=sorted({d.kind.value for d in blocking}),
                )
            )
        else:
            receipt._accepted()
        return receipt

    @property
    def total(self) -> Decimal:
        return sum((line.amount for line in self.lines), Decimal(0))

    @property
    def expected_total(self) -> Decimal:
        return sum((line.expected_amount for line in self.lines), Decimal(0))

    @property
    def is_complete(self) -> bool:
        """Buyurtma to'liq keldimi (kam kelgan pozitsiya yo'q) — PO holati uchun."""
        return all(line.qty_fact >= line.qty_expected for line in self.lines)

    def resolve_dispute(self, *, by: UUID, resolution: Resolution, comment: str, at: datetime) -> None:
        if self.status is not ReceiptStatus.DISPUTED or self.dispute is None or not self.dispute.is_open:
            raise InvalidTransitionError("receipt.no_open_dispute")
        text = _clean(comment)
        if not text:
            raise InvalidReceiptError("receipt.comment_required")
        self.dispute.resolution = resolution
        self.dispute.comment = text
        self.dispute.resolved_by = by
        self.dispute.resolved_at = at
        self.status = ReceiptStatus.ACCEPTED
        self._accepted()

    def _accepted(self) -> None:
        self.record(
            ReceiptAccepted(
                aggregate_id=self.id,
                number=self.number,
                order_id=str(self.header.order_id),
                store_id=str(self.header.store_id),
                supplier_id=str(self.header.supplier_id),
                amount=str(self.total),
                received_at=self.header.received_at.isoformat(),
                had_dispute=self.dispute is not None,
            )
        )


def _line(line_id: UUID, expected: ExpectedLine, fact: FactLine | None) -> ReceiptLine:
    """Fakt kiritilmagan pozitsiya — umuman kelmagan (qty 0)."""
    qty = fact.qty if fact else Decimal(0)
    price = fact.price if fact else expected.price
    defect = fact.qty_defect if fact else Decimal(0)
    if not qty.is_finite() or qty < 0 or not price.is_finite() or price < 0:
        raise InvalidReceiptError("receipt.negative")
    if not defect.is_finite() or defect < 0 or defect > qty:
        raise InvalidReceiptError("receipt.defect_range")
    if defect > 0 and not _clean(fact.defect_reason if fact else None):
        raise InvalidReceiptError("receipt.defect_reason_required")
    return ReceiptLine(
        id=line_id,
        order_line_id=expected.order_line_id,
        product_id=expected.product_id,
        base_unit=expected.base_unit,
        qty_expected=expected.qty,
        price_expected=expected.price,
        qty_fact=qty.quantize(QTY, ROUND_HALF_UP),
        price_fact=price.quantize(QTY, ROUND_HALF_UP),
        qty_defect=defect.quantize(QTY, ROUND_HALF_UP),
        defect_reason=_clean(fact.defect_reason) if fact else None,
    )


def _pct(expected: Decimal, actual: Decimal) -> Decimal:
    return abs(actual - expected) / expected * 100 if expected else Decimal(100)


def _discrepancies(line: ReceiptLine, tolerance: ReceivingTolerance) -> list[Discrepancy]:
    found = []
    if line.qty_fact == 0 and line.qty_expected > 0:
        found.append(Discrepancy(line.id, DiscrepancyKind.SHORT, line.qty_expected, line.qty_fact, False))
    elif line.qty_fact != line.qty_expected:
        kind = DiscrepancyKind.QTY_OVER if line.qty_fact > line.qty_expected else DiscrepancyKind.QTY_UNDER
        within = _pct(line.qty_expected, line.qty_fact) <= tolerance.qty_pct(line.base_unit)
        found.append(Discrepancy(line.id, kind, line.qty_expected, line.qty_fact, within))
    if line.price_fact > line.price_expected:
        within = _pct(line.price_expected, line.price_fact) <= tolerance.price_pct
        found.append(Discrepancy(line.id, DiscrepancyKind.PRICE_UP, line.price_expected, line.price_fact, within))
    elif line.price_fact < line.price_expected:
        found.append(Discrepancy(line.id, DiscrepancyKind.PRICE_DOWN, line.price_expected, line.price_fact, True))
    if line.qty_defect > 0:
        found.append(Discrepancy(line.id, DiscrepancyKind.DEFECT, Decimal(0), line.qty_defect, False))
    return found


def _clean(text: str | None) -> str | None:
    cleaned = " ".join((text or "").split())[:MAX_TEXT]
    return cleaned or None
