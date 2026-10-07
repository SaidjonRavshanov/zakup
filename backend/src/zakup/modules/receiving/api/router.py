"""Qabul HTTP API. Biznes qoidalar va ruxsat — use case / domain'da."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from zakup.modules.receiving.application.dto import FactLineData, SubmitReceiptCommand
from zakup.modules.receiving.application.use_cases import (
    MAX_FILE_BYTES,
    GetAttachment,
    GetOrderToReceive,
    GetReceipt,
    ListReceipts,
    ResolveDispute,
    SubmitReceipt,
    UploadAttachment,
)
from zakup.modules.receiving.domain.receipt import (
    DiscrepancyKind,
    InvalidReceiptError,
    PaymentMethod,
    ReceiptStatus,
    Resolution,
)
from zakup.platform.di import Stub
from zakup.platform.i18n import negotiate_locale, translate
from zakup.platform.security import CurrentPrincipal

router = APIRouter(prefix="/receiving", tags=["receiving"])

Qty = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=4)]


def use(cls: type) -> Any:
    return Depends(Stub(cls))


class Model(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ExpectedLineOut(Model):
    order_line_id: UUID
    product_id: UUID
    product_name: str
    base_unit: str
    qty: Decimal
    price: Decimal


class ExpectedOrderOut(Model):
    order_id: UUID
    number: str
    store_id: UUID
    supplier_id: UUID
    lines: list[ExpectedLineOut]


class FactLineIn(BaseModel):
    order_line_id: UUID
    qty: Qty
    price: Qty
    qty_defect: Qty = Decimal(0)
    defect_reason: str | None = Field(default=None, max_length=500)


class SubmitReceiptIn(BaseModel):
    id: UUID = Field(description="Klientda yaratilgan UUIDv7 — qayta yuborishda o'zgarmaydi (idempotentlik)")
    order_id: UUID
    invoice_photo_id: UUID
    supplier_invoice_no: str | None = Field(default=None, max_length=100)
    payment_method: PaymentMethod | None = None
    comment: str | None = Field(default=None, max_length=500)
    lines: list[FactLineIn] = Field(max_length=300)
    captured_at: datetime | None = Field(
        default=None, description="Oflayn: qabul telefonda qachon rasmiylashtirilgan (yuborilgan vaqt emas)"
    )


class StatusOut(BaseModel):
    status: ReceiptStatus


class CreatedOut(BaseModel):
    id: UUID


class ResolveIn(BaseModel):
    resolution: Resolution
    comment: str = Field(min_length=1, max_length=500)


class ReceiptListOut(Model):
    id: UUID
    number: str
    order_id: UUID
    store_id: UUID
    store_name: str | None
    supplier_id: UUID
    supplier_name: str | None
    status: ReceiptStatus
    total: Decimal
    expected_total: Decimal
    received_at: datetime
    dispute_open: bool
    export_status: str | None


class ReceiptLineOut(Model):
    id: UUID
    product_id: UUID
    product_name: str
    base_unit: str
    qty_expected: Decimal
    price_expected: Decimal
    qty_fact: Decimal
    price_fact: Decimal
    qty_defect: Decimal
    defect_reason: str | None
    amount: Decimal


class DiscrepancyOut(Model):
    line_id: UUID
    kind: DiscrepancyKind
    expected: Decimal
    actual: Decimal
    within_tolerance: bool


class DisputeOut(Model):
    opened_at: datetime
    resolution: Resolution | None
    comment: str | None
    resolved_by: UUID | None
    resolved_at: datetime | None


class ReceiptDetailOut(Model):
    id: UUID
    number: str
    order_id: UUID
    store_id: UUID
    store_name: str | None
    supplier_id: UUID
    supplier_name: str | None
    status: ReceiptStatus
    received_by: UUID
    received_at: datetime
    supplier_invoice_no: str | None
    payment_method: PaymentMethod | None
    invoice_photo_id: UUID
    comment: str | None
    total: Decimal
    expected_total: Decimal
    lines: list[ReceiptLineOut]
    discrepancies: list[DiscrepancyOut]
    dispute: DisputeOut | None
    export_status: str | None
    export_error: str | None
    iiko_document_number: str | None


@router.get("/orders/{order_id}/expected")
async def order_to_receive(
    order_id: UUID, actor: CurrentPrincipal, use_case: Annotated[GetOrderToReceive, use(GetOrderToReceive)]
) -> ExpectedOrderOut:
    return ExpectedOrderOut.model_validate(await use_case(actor, order_id))


@router.post("/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    request: Request,
    actor: CurrentPrincipal,
    use_case: Annotated[UploadAttachment, use(UploadAttachment)],
    content_type: Annotated[str, Header()] = "application/octet-stream",
    content_length: Annotated[int | None, Header()] = None,
) -> CreatedOut:
    """Xom tana (multipart'siz): `Content-Type: image/jpeg`. Klient rasmni oldindan siqadi."""
    if content_length is not None and content_length > MAX_FILE_BYTES:
        raise InvalidReceiptError("receipt.file_size", max_mb=MAX_FILE_BYTES // 1024 // 1024)
    body = await request.body()
    return CreatedOut(id=await use_case(actor, content=body, content_type=content_type.split(";")[0].strip()))


@router.get("/attachments/{file_id}")
async def download_attachment(
    file_id: UUID, actor: CurrentPrincipal, use_case: Annotated[GetAttachment, use(GetAttachment)]
) -> Response:
    stored = await use_case(actor, file_id)
    return Response(stored.content, media_type=stored.content_type, headers={"Cache-Control": "private, max-age=86400"})


@router.post("/receipts")
async def submit_receipt(
    body: SubmitReceiptIn, actor: CurrentPrincipal, use_case: Annotated[SubmitReceipt, use(SubmitReceipt)]
) -> StatusOut:
    command = SubmitReceiptCommand(
        id=body.id,
        order_id=body.order_id,
        invoice_photo_id=body.invoice_photo_id,
        supplier_invoice_no=body.supplier_invoice_no,
        payment_method=body.payment_method,
        comment=body.comment,
        lines=tuple(FactLineData(**line.model_dump()) for line in body.lines),
        captured_at=body.captured_at,
    )
    return StatusOut(status=await use_case(actor, command))


@router.get("/receipts")
async def list_receipts(
    actor: CurrentPrincipal,
    use_case: Annotated[ListReceipts, use(ListReceipts)],
    status_in: Annotated[list[ReceiptStatus] | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[ReceiptListOut]:
    items = await use_case(actor, statuses=set(status_in) if status_in else None, limit=limit)
    return [ReceiptListOut.model_validate(item) for item in items]


@router.get("/receipts/{receipt_id}")
async def get_receipt(
    receipt_id: UUID, request: Request, actor: CurrentPrincipal, use_case: Annotated[GetReceipt, use(GetReceipt)]
) -> ReceiptDetailOut:
    out = ReceiptDetailOut.model_validate(await use_case(actor, receipt_id))
    if out.export_error:
        # Eksport xatosi i18n kaliti bo'lib saqlanadi (masalan, iiko.supplier_not_linked) — so'rov tilida
        out.export_error = translate(out.export_error, negotiate_locale(request.headers.get("accept-language")))
    return out


@router.post("/receipts/{receipt_id}/resolve", status_code=status.HTTP_204_NO_CONTENT)
async def resolve_dispute(
    receipt_id: UUID, body: ResolveIn, actor: CurrentPrincipal, use_case: Annotated[ResolveDispute, use(ResolveDispute)]
) -> None:
    await use_case(actor, receipt_id, resolution=body.resolution, comment=body.comment)
