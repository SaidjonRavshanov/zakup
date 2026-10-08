from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from zakup.modules.finance.domain.finance import ObligationStatus, PaymentMethod, PaymentStatus


@dataclass(frozen=True, slots=True)
class ObligationView:
    id: UUID
    receipt_id: UUID
    receipt_number: str
    supplier_id: UUID
    store_id: UUID
    amount: Decimal
    paid: Decimal
    outstanding: Decimal
    received_on: date
    due_date: date
    status: ObligationStatus
    overdue: bool = False
    reserved: Decimal = Decimal(0)  # faol to'lov zayavkalarida band
    store_name: str | None = None


@dataclass(frozen=True, slots=True)
class SupplierBalance:
    supplier_id: UUID
    supplier_name: str | None
    debt: Decimal  # to'lanadigan (bloklanmagan) qoldiq
    blocked: Decimal  # nizo ochiq nakladnoylar
    overdue: Decimal
    reserved: Decimal
    credit_limit: Decimal | None  # None — limit yo'q
    free_limit: Decimal | None
    nearest_due: date | None
    open_count: int


@dataclass(frozen=True, slots=True)
class SupplierAccount:
    balance: SupplierBalance
    obligations: tuple[ObligationView, ...]


@dataclass(frozen=True, slots=True)
class PaymentLineView:
    obligation_id: UUID
    receipt_id: UUID
    receipt_number: str
    amount: Decimal
    outstanding: Decimal


@dataclass(frozen=True, slots=True)
class PaymentListItem:
    id: UUID
    number: str
    supplier_id: UUID
    method: PaymentMethod
    status: PaymentStatus
    total: Decimal
    requested_at: datetime
    paid_at: datetime | None
    supplier_name: str | None = None
    comment: str | None = None


@dataclass(frozen=True, slots=True)
class PaymentDetail:
    id: UUID
    number: str
    supplier_id: UUID
    method: PaymentMethod
    status: PaymentStatus
    total: Decimal
    requested_by: UUID
    requested_at: datetime
    comment: str | None
    approved_by: UUID | None
    approved_at: datetime | None
    decision_comment: str | None
    paid_by: UUID | None
    paid_at: datetime | None
    proof_id: UUID | None
    lines: tuple[PaymentLineView, ...] = field(default=())
    supplier_name: str | None = None


@dataclass(frozen=True, slots=True)
class NewPaymentLine:
    obligation_id: UUID
    amount: Decimal


@dataclass(frozen=True, slots=True)
class CreatePaymentCommand:
    supplier_id: UUID
    method: PaymentMethod
    lines: tuple[NewPaymentLine, ...]
    comment: str | None = None
