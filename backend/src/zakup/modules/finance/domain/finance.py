"""To'lovlar (WORKFLOW B12): qarz nakladnoy bo'yicha hisoblanadi, "umuman yetkazuvchi bo'yicha" emas.

- Har bir qabul qilingan nakladnoy = `Obligation` (majburiyat), muddati = qabul sanasi + kechiktirish kunlari.
- Nizo ochiq — majburiyat bloklangan: to'lab bo'lmaydi.
- Buxgalter `PaymentRequest` (to'lov zayavkasi) tuzadi: aniq nakladnoylar va summalar (qisman to'lash mumkin).
  Tasdiqlangach to'lanadi — summa shu nakladnoylarga taqsimlanadi (saldo doim yaqinlashadi).
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from typing import ClassVar
from uuid import UUID

from zakup.shared_kernel.errors import DomainError, InvalidTransitionError
from zakup.shared_kernel.events import AggregateRoot, DomainEvent

ZERO = Decimal(0)


class InvalidPaymentError(DomainError):
    code = "invalid_payment"


class ObligationStatus(StrEnum):
    OPEN = "OPEN"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    BLOCKED = "BLOCKED"  # nizo ochiq


class PaymentMethod(StrEnum):
    CASH = "cash"
    TRANSFER = "transfer"


class PaymentStatus(StrEnum):
    SUBMITTED = "SUBMITTED"  # tasdiq kutilmoqda
    APPROVED = "APPROVED"
    PAID = "PAID"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


ACTIVE_PAYMENT_STATUSES = frozenset({PaymentStatus.SUBMITTED, PaymentStatus.APPROVED})
ON_DELIVERY_COMMENT = "Оплачено при приёмке"  # tizim yozadi; frontend shu bo'yicha belgilamaydi — faqat matn


@dataclass(kw_only=True)
class Obligation:
    id: UUID
    receipt_id: UUID
    receipt_number: str
    supplier_id: UUID
    store_id: UUID
    amount: Decimal
    paid: Decimal = ZERO
    received_on: date
    due_date: date
    blocked: bool = False
    version: int = 1

    @classmethod
    def from_receipt(
        cls,
        *,
        id: UUID,  # noqa: A002
        receipt_id: UUID,
        receipt_number: str,
        supplier_id: UUID,
        store_id: UUID,
        amount: Decimal,
        received_on: date,
        deferral_days: int,
        blocked: bool,
    ) -> "Obligation":
        if amount < 0:
            raise InvalidPaymentError("payment.amount_invalid")
        return cls(
            id=id,
            receipt_id=receipt_id,
            receipt_number=receipt_number,
            supplier_id=supplier_id,
            store_id=store_id,
            amount=amount,
            received_on=received_on,
            due_date=received_on + timedelta(days=max(deferral_days, 0)),
            blocked=blocked,
        )

    @property
    def outstanding(self) -> Decimal:
        return max(self.amount - self.paid, ZERO)

    @property
    def status(self) -> ObligationStatus:
        if self.outstanding == 0:
            return ObligationStatus.PAID
        if self.blocked:
            return ObligationStatus.BLOCKED
        return ObligationStatus.PARTIALLY_PAID if self.paid > 0 else ObligationStatus.OPEN

    def is_overdue(self, today: date) -> bool:
        return not self.blocked and self.outstanding > 0 and self.due_date < today

    def accept(self, amount: Decimal) -> None:
        """Nizo yopildi: blok yechiladi, summa — yakuniy qabul summasi."""
        if amount < self.paid:
            raise InvalidPaymentError("payment.amount_below_paid")
        self.amount = amount
        self.blocked = False

    def allocate(self, amount: Decimal) -> None:
        if self.blocked:
            raise InvalidPaymentError("payment.obligation_blocked", number=self.receipt_number)
        if amount <= 0 or amount > self.outstanding:
            raise InvalidPaymentError("payment.over_outstanding", number=self.receipt_number)
        self.paid += amount


@dataclass(frozen=True, kw_only=True)
class PaymentPaid(DomainEvent):
    """To'lov amalga oshdi → bildirishnoma, analitika."""

    event_type: ClassVar[str] = "finance.payment_paid"
    supplier_id: str
    amount: str
    method: str


@dataclass(frozen=True, kw_only=True)
class PaymentSubmitted(DomainEvent):
    """To'lov zayavkasi yaratildi → bot: tasdiqlovchiga (yoki tasdiq shart bo'lmasa — buxgalterga)."""

    event_type: ClassVar[str] = "finance.payment_submitted"
    supplier_id: str
    amount: str
    method: str
    status: str


@dataclass(frozen=True, kw_only=True)
class PaymentApproved(DomainEvent):
    """Tasdiqlandi → bot: buxgalterga "to'lash kerak"."""

    event_type: ClassVar[str] = "finance.payment_approved"
    supplier_id: str
    amount: str


@dataclass(frozen=True, kw_only=True)
class PaymentRejected(DomainEvent):
    """Rad etildi → bot: zayavka muallifiga."""

    event_type: ClassVar[str] = "finance.payment_rejected"
    requested_by: str
    comment: str


@dataclass(frozen=True, slots=True)
class PaymentLine:
    obligation_id: UUID
    amount: Decimal


@dataclass(eq=False)
class PaymentRequest(AggregateRoot):
    aggregate_type: ClassVar[str] = "finance.payment_request"

    id: UUID
    number: str
    supplier_id: UUID
    method: PaymentMethod
    lines: list[PaymentLine]
    status: PaymentStatus
    requested_by: UUID
    requested_at: datetime
    comment: str | None = None
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    decision_comment: str | None = None
    paid_by: UUID | None = None
    paid_at: datetime | None = None
    proof_id: UUID | None = None
    version: int = 1

    @classmethod
    def create(
        cls,
        *,
        id: UUID,  # noqa: A002
        number: str,
        supplier_id: UUID,
        method: PaymentMethod,
        lines: list[PaymentLine],
        requested_by: UUID,
        at: datetime,
        comment: str | None,
        approval_required: bool,
    ) -> "PaymentRequest":
        if not lines:
            raise InvalidPaymentError("payment.no_lines")
        if len({line.obligation_id for line in lines}) != len(lines):
            raise InvalidPaymentError("payment.duplicate_line")
        if any(line.amount <= 0 for line in lines):
            raise InvalidPaymentError("payment.amount_invalid")
        request = cls(
            id=id,
            number=number,
            supplier_id=supplier_id,
            method=method,
            lines=lines,
            status=PaymentStatus.SUBMITTED if approval_required else PaymentStatus.APPROVED,
            requested_by=requested_by,
            requested_at=at,
            comment=_clean(comment),
        )
        if not approval_required:
            request.approved_by, request.approved_at = requested_by, at
        request.record(
            PaymentSubmitted(
                aggregate_id=id,
                supplier_id=str(supplier_id),
                amount=str(request.total),
                method=method.value,
                status=request.status.value,
            )
        )
        return request

    @classmethod
    def paid_on_delivery(
        cls,
        *,
        id: UUID,  # noqa: A002
        number: str,
        obligation: Obligation,
        method: PaymentMethod,
        paid_by: UUID,
        at: datetime,
    ) -> "PaymentRequest":
        """Qabulda yetkazuvchiga joyida to'langan: tasdiqsiz, darhol PAID.

        Buxgalter "Оплаты"da solishtirish uchun ko'radi, auditor — nazoratda (chek yo'q to'lov).
        """
        amount = obligation.outstanding
        request = cls(
            id=id,
            number=number,
            supplier_id=obligation.supplier_id,
            method=method,
            lines=[PaymentLine(obligation.id, amount)],
            status=PaymentStatus.APPROVED,
            requested_by=paid_by,
            requested_at=at,
            comment=ON_DELIVERY_COMMENT,
        )
        request.pay({obligation.id: obligation}, by=paid_by, at=at, proof_id=None)
        return request

    def __post_init__(self) -> None:
        AggregateRoot.__init__(self)

    @property
    def total(self) -> Decimal:
        return sum((line.amount for line in self.lines), ZERO)

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_PAYMENT_STATUSES

    def approve(self, *, by: UUID, at: datetime) -> None:
        self._require(PaymentStatus.SUBMITTED)
        self.status = PaymentStatus.APPROVED
        self.approved_by, self.approved_at = by, at
        self.record(PaymentApproved(aggregate_id=self.id, supplier_id=str(self.supplier_id), amount=str(self.total)))

    def reject(self, *, by: UUID, comment: str, at: datetime) -> None:
        self._require(PaymentStatus.SUBMITTED, PaymentStatus.APPROVED)
        text = _clean(comment)
        if not text:
            raise InvalidPaymentError("payment.comment_required")
        self.status = PaymentStatus.REJECTED
        self.approved_by, self.approved_at, self.decision_comment = by, at, text
        self.record(PaymentRejected(aggregate_id=self.id, requested_by=str(self.requested_by), comment=text))

    def cancel(self) -> None:
        self._require(PaymentStatus.SUBMITTED, PaymentStatus.APPROVED)
        self.status = PaymentStatus.CANCELLED

    def pay(self, obligations: dict[UUID, Obligation], *, by: UUID, at: datetime, proof_id: UUID | None) -> None:
        """Summalar aniq nakladnoylarga taqsimlanadi (majburiyatlar shu tranzaksiyada saqlanadi)."""
        self._require(PaymentStatus.APPROVED)
        for line in self.lines:
            obligation = obligations.get(line.obligation_id)
            if obligation is None or obligation.supplier_id != self.supplier_id:
                raise InvalidPaymentError("payment.obligation_not_found")
            obligation.allocate(line.amount)
        self.status = PaymentStatus.PAID
        self.paid_by, self.paid_at, self.proof_id = by, at, proof_id
        self.record(
            PaymentPaid(
                aggregate_id=self.id,
                supplier_id=str(self.supplier_id),
                amount=str(self.total),
                method=self.method.value,
            )
        )

    def _require(self, *statuses: PaymentStatus) -> None:
        if self.status not in statuses:
            raise InvalidTransitionError("payment.invalid_status")


def _clean(text: str | None) -> str | None:
    text = (text or "").strip()
    return text[:500] or None
