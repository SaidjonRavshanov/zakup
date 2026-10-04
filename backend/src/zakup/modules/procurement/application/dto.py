from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from zakup.modules.procurement.domain.approval import Decision
from zakup.modules.procurement.domain.order import Channel, OrderStatus, ResponseKind
from zakup.modules.procurement.domain.request import LineDecision, RequestStatus, RequestType

# ---------------------------------------------------------------- catalog'dan keladigan ma'lumot


@dataclass(frozen=True, slots=True)
class OfferInfo:
    offer_id: UUID
    supplier_id: UUID
    product_id: UUID
    pack_unit: str
    pack_factor: Decimal
    price_per_pack: Decimal
    price_per_base: Decimal
    supplier_sku: str | None
    available: bool


@dataclass(frozen=True, slots=True)
class SupplierInfo:
    supplier_id: UUID
    name: str
    min_order_amount: Decimal
    lead_time_days: int
    phone: str | None
    telegram: str | None


@dataclass(frozen=True, slots=True)
class CatalogLabels:
    products: dict[UUID, tuple[str, str]]  # (nom, bazaviy birlik)
    suppliers: dict[UUID, str]
    stores: dict[UUID, str]

    def product(self, product_id: UUID) -> tuple[str, str]:
        return self.products.get(product_id, ("?", "pcs"))


# ---------------------------------------------------------------- zayavka


@dataclass(frozen=True, slots=True)
class RequestListItem:
    id: UUID
    number: str
    store_id: UUID
    type: RequestType
    status: RequestStatus
    needed_by: date
    initiator_id: UUID
    total: Decimal
    lines_count: int
    created_at: datetime
    store_name: str | None = None


@dataclass(frozen=True, slots=True)
class RequestLineView:
    id: UUID
    product_id: UUID
    qty: Decimal
    note: str | None
    offer_id: UUID | None
    supplier_id: UUID | None
    price_per_base: Decimal | None
    amount: Decimal
    decision: LineDecision
    product_name: str = ""
    base_unit: str = "pcs"
    supplier_name: str | None = None


@dataclass(frozen=True, slots=True)
class ApprovalView:
    approver_id: UUID
    decision: Decision
    comment: str | None
    amount: Decimal
    role_conflict: bool
    decided_at: datetime


@dataclass(frozen=True, slots=True)
class RequestDetail:
    id: UUID
    number: str
    store_id: UUID
    type: RequestType
    status: RequestStatus
    needed_by: date
    initiator_id: UUID
    comment: str | None
    total: Decimal
    created_at: datetime
    lines: tuple[RequestLineView, ...]
    approvals: tuple[ApprovalView, ...]
    version: int
    store_name: str | None = None
    orders: tuple["OrderListItem", ...] = ()


# ---------------------------------------------------------------- buyurtma (PO)


@dataclass(frozen=True, slots=True)
class OrderListItem:
    id: UUID
    number: str
    request_id: UUID | None
    supplier_id: UUID
    store_id: UUID
    delivery_date: date
    status: OrderStatus
    total: Decimal
    confirmed_total: Decimal
    lines_count: int
    sent_at: datetime | None
    response_deadline: datetime | None
    created_at: datetime
    supplier_name: str | None = None
    store_name: str | None = None


@dataclass(frozen=True, slots=True)
class OrderLineView:
    id: UUID
    product_id: UUID
    offer_id: UUID
    pack_unit: str
    pack_factor: Decimal
    qty_packs: Decimal
    price_per_pack: Decimal
    amount: Decimal
    response: ResponseKind | None
    qty_confirmed: Decimal | None
    price_confirmed: Decimal | None
    needs_reapproval: bool
    product_name: str = ""
    base_unit: str = "pcs"


@dataclass(frozen=True, slots=True)
class OrderDetail:
    id: UUID
    number: str
    request_id: UUID | None
    supplier_id: UUID
    store_id: UUID
    delivery_date: date
    status: OrderStatus
    total: Decimal
    confirmed_total: Decimal
    sent_at: datetime | None
    sent_channel: Channel | None
    response_deadline: datetime | None
    responded_at: datetime | None
    cancel_reason: str | None
    created_at: datetime
    lines: tuple[OrderLineView, ...]
    version: int
    supplier_name: str | None = None
    supplier_phone: str | None = None
    supplier_telegram: str | None = None
    min_order_amount: Decimal = Decimal(0)
    store_name: str | None = None
    warnings: tuple[str, ...] = field(default=())


@dataclass(frozen=True, slots=True)
class SentOrder:
    """Yuborish natijasi: yetkazuvchiga jo'natiladigan matn va javob havolasi (Telegram/WhatsApp'ga ulashish)."""

    message: str
    response_url: str
