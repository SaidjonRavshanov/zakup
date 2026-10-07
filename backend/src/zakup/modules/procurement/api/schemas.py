from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zakup.modules.procurement.domain.approval import Decision
from zakup.modules.procurement.domain.order import Channel, LineResponse, OrderStatus, ResponseKind
from zakup.modules.procurement.domain.request import LineDecision, RequestStatus, RequestType

Qty = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=4)]
Price = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=4)]
Comment = Annotated[str, Field(min_length=1, max_length=500)]


class Model(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- zayavka


class CreateRequestIn(BaseModel):
    store_id: UUID
    needed_by: date
    type: RequestType = RequestType.MANUAL
    comment: str | None = Field(default=None, max_length=500)


class ReviseRequestIn(BaseModel):
    needed_by: date
    comment: str | None = Field(default=None, max_length=500)


class AddLineIn(BaseModel):
    product_id: UUID
    qty: Qty
    note: str | None = Field(default=None, max_length=500)


class ChangeLineIn(BaseModel):
    qty: Qty
    note: str | None = Field(default=None, max_length=500)


class ChooseOfferIn(BaseModel):
    offer_id: UUID | None


class ApproveIn(BaseModel):
    """`line_ids` bo'lmasa — butun zayavka; bo'lsa — qisman tasdiqlash (qolganlari rad etiladi)."""

    line_ids: list[UUID] | None = Field(default=None, max_length=300)


class CommentIn(BaseModel):
    comment: Comment


class CreatedOut(BaseModel):
    id: UUID


class ApprovedOut(BaseModel):
    order_ids: list[UUID]


class RequestListOut(Model):
    id: UUID
    number: str
    store_id: UUID
    store_name: str | None
    type: RequestType
    status: RequestStatus
    needed_by: date
    initiator_id: UUID
    total: Decimal
    lines_count: int
    created_at: datetime


class RequestLineOut(Model):
    id: UUID
    product_id: UUID
    product_name: str
    base_unit: str
    qty: Decimal
    note: str | None
    offer_id: UUID | None
    supplier_id: UUID | None
    supplier_name: str | None
    price_per_base: Decimal | None
    amount: Decimal
    decision: LineDecision
    qty_suggested: Decimal | None = None
    calc: dict[str, str | None] | None = None
    pack_unit: str | None = None
    pack_factor: Decimal | None = None
    qty_packs: Decimal | None = None
    order_amount: Decimal | None = None


class ApprovalOut(Model):
    approver_id: UUID
    decision: Decision
    comment: str | None
    amount: Decimal
    role_conflict: bool
    decided_at: datetime


class OrderListOut(Model):
    id: UUID
    number: str
    request_id: UUID | None
    supplier_id: UUID
    supplier_name: str | None
    store_id: UUID
    store_name: str | None
    delivery_date: date
    status: OrderStatus
    total: Decimal
    confirmed_total: Decimal
    lines_count: int
    sent_at: datetime | None
    response_deadline: datetime | None
    created_at: datetime


class RequestDetailOut(Model):
    id: UUID
    number: str
    store_id: UUID
    store_name: str | None
    type: RequestType
    status: RequestStatus
    needed_by: date
    initiator_id: UUID
    comment: str | None
    total: Decimal
    created_at: datetime
    lines: list[RequestLineOut]
    approvals: list[ApprovalOut]
    orders: list[OrderListOut]
    order_total: Decimal | None = None


# ---------------------------------------------------------------- buyurtma


class OrderLineOut(Model):
    id: UUID
    product_id: UUID
    product_name: str
    base_unit: str
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


class OrderDetailOut(Model):
    id: UUID
    number: str
    request_id: UUID | None
    supplier_id: UUID
    supplier_name: str | None
    supplier_phone: str | None
    supplier_telegram: str | None
    store_id: UUID
    store_name: str | None
    delivery_date: date
    status: OrderStatus
    total: Decimal
    confirmed_total: Decimal
    min_order_amount: Decimal
    sent_at: datetime | None
    sent_channel: Channel | None
    response_deadline: datetime | None
    responded_at: datetime | None
    cancel_reason: str | None
    created_at: datetime
    lines: list[OrderLineOut]
    warnings: list[str]


class SendOrderIn(BaseModel):
    channel: Channel


class SentOrderOut(Model):
    message: str
    response_url: str


class LineResponseIn(BaseModel):
    line_id: UUID
    kind: ResponseKind
    qty_packs: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=4)] | None = None
    price_per_pack: Price | None = None


class OrderResponseIn(BaseModel):
    lines: list[LineResponseIn] = Field(max_length=300)

    def to_domain(self) -> dict[UUID, LineResponse]:
        return {
            line.line_id: LineResponse(kind=line.kind, qty_packs=line.qty_packs, price_per_pack=line.price_per_pack)
            for line in self.lines
        }


class StatusOut(BaseModel):
    status: OrderStatus


class CancelOrderIn(BaseModel):
    reason: Comment


# ---------------------------------------------------------------- yetkazuvchi uchun (ro'yxatsiz)


class PublicOrderLineOut(Model):
    id: UUID
    product_name: str
    pack_unit: str
    pack_factor: Decimal
    base_unit: str
    qty_packs: Decimal
    price_per_pack: Decimal
    amount: Decimal
    response: ResponseKind | None
    qty_confirmed: Decimal | None
    price_confirmed: Decimal | None


class PublicOrderOut(Model):
    number: str
    supplier_name: str | None
    store_name: str | None
    delivery_date: date
    status: OrderStatus
    total: Decimal
    lines: list[PublicOrderLineOut]
