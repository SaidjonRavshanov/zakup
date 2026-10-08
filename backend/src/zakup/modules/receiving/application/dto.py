from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from zakup.modules.receiving.domain.receipt import DiscrepancyKind, PaymentMethod, ReceiptStatus, Resolution


@dataclass(frozen=True, slots=True)
class FactLineData:
    order_line_id: UUID
    qty: Decimal
    price: Decimal
    qty_defect: Decimal = Decimal(0)
    defect_reason: str | None = None


@dataclass(frozen=True, slots=True)
class SubmitReceiptCommand:
    id: UUID  # klient (oflayn) yaratgan — idempotentlik kaliti
    order_id: UUID
    invoice_photo_id: UUID
    supplier_invoice_no: str | None
    payment_method: PaymentMethod | None
    comment: str | None
    lines: tuple[FactLineData, ...]
    captured_at: datetime | None = None  # oflayn qabul vaqti (telefonda); None — server vaqti
    paid_on_delivery: bool = False


@dataclass(frozen=True, slots=True)
class ReceiptListItem:
    id: UUID
    number: str
    order_id: UUID
    order_number: str | None
    store_id: UUID
    supplier_id: UUID
    status: ReceiptStatus
    total: Decimal
    expected_total: Decimal
    received_at: datetime
    dispute_open: bool
    export_status: str | None
    store_name: str | None = None
    supplier_name: str | None = None


@dataclass(frozen=True, slots=True)
class ReceiptLineView:
    id: UUID
    product_id: UUID
    base_unit: str
    qty_expected: Decimal
    price_expected: Decimal
    qty_fact: Decimal
    price_fact: Decimal
    qty_defect: Decimal
    defect_reason: str | None
    amount: Decimal
    product_name: str = ""


@dataclass(frozen=True, slots=True)
class DiscrepancyView:
    line_id: UUID
    kind: DiscrepancyKind
    expected: Decimal
    actual: Decimal
    within_tolerance: bool


@dataclass(frozen=True, slots=True)
class DisputeView:
    opened_at: datetime
    resolution: Resolution | None
    comment: str | None
    resolved_by: UUID | None
    resolved_at: datetime | None


@dataclass(frozen=True, slots=True)
class ReceiptDetail:
    id: UUID
    number: str
    order_id: UUID
    order_number: str | None
    store_id: UUID
    supplier_id: UUID
    status: ReceiptStatus
    received_by: UUID
    received_at: datetime
    supplier_invoice_no: str | None
    payment_method: PaymentMethod | None
    invoice_photo_id: UUID
    comment: str | None
    total: Decimal
    expected_total: Decimal
    lines: tuple[ReceiptLineView, ...]
    discrepancies: tuple[DiscrepancyView, ...]
    dispute: DisputeView | None
    export_status: str | None
    export_error: str | None
    iiko_document_number: str | None
    paid_on_delivery: bool = False
    store_name: str | None = None
    supplier_name: str | None = None
