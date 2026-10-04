"""To'lovlar HTTP API. Biznes qoidalar va ruxsat — use case / domain'da."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from zakup.modules.finance.application.dto import CreatePaymentCommand, NewPaymentLine
from zakup.modules.finance.application.use_cases import (
    MAX_FILE_BYTES,
    ApprovePayment,
    CancelPayment,
    CreatePayment,
    GetPayment,
    GetProof,
    GetSupplierAccount,
    ListBalances,
    ListPayments,
    PayPayment,
    RejectPayment,
    UploadProof,
)
from zakup.modules.finance.domain.finance import InvalidPaymentError, ObligationStatus, PaymentMethod, PaymentStatus
from zakup.platform.di import Stub
from zakup.platform.security import CurrentPrincipal

router = APIRouter(prefix="/finance", tags=["finance"])

Amount = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]


def use(cls: type) -> Any:
    return Depends(Stub(cls))


class Model(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class BalanceOut(Model):
    supplier_id: UUID
    supplier_name: str | None
    debt: Decimal
    blocked: Decimal
    overdue: Decimal
    reserved: Decimal
    credit_limit: Decimal | None
    free_limit: Decimal | None
    nearest_due: date | None
    open_count: int


class ObligationOut(Model):
    id: UUID
    receipt_id: UUID
    receipt_number: str
    store_id: UUID
    store_name: str | None
    amount: Decimal
    paid: Decimal
    outstanding: Decimal
    reserved: Decimal
    received_on: date
    due_date: date
    status: ObligationStatus
    overdue: bool


class AccountOut(Model):
    balance: BalanceOut
    obligations: list[ObligationOut]


class PaymentLineIn(BaseModel):
    obligation_id: UUID
    amount: Amount


class CreatePaymentIn(BaseModel):
    supplier_id: UUID
    method: PaymentMethod
    comment: str | None = Field(default=None, max_length=500)
    lines: list[PaymentLineIn] = Field(min_length=1, max_length=200)


class CreatedOut(BaseModel):
    id: UUID


class RejectIn(BaseModel):
    comment: str = Field(min_length=1, max_length=500)


class PayIn(BaseModel):
    proof_id: UUID | None = None


class PaymentListOut(Model):
    id: UUID
    number: str
    supplier_id: UUID
    supplier_name: str | None
    method: PaymentMethod
    status: PaymentStatus
    total: Decimal
    requested_at: datetime
    paid_at: datetime | None


class PaymentLineOut(Model):
    obligation_id: UUID
    receipt_id: UUID
    receipt_number: str
    amount: Decimal
    outstanding: Decimal


class PaymentDetailOut(PaymentListOut):
    requested_by: UUID
    comment: str | None
    approved_by: UUID | None
    approved_at: datetime | None
    decision_comment: str | None
    paid_by: UUID | None
    proof_id: UUID | None
    lines: list[PaymentLineOut]


@router.get("/suppliers")
async def list_balances(
    actor: CurrentPrincipal, use_case: Annotated[ListBalances, use(ListBalances)]
) -> list[BalanceOut]:
    return [BalanceOut.model_validate(item) for item in await use_case(actor)]


@router.get("/suppliers/{supplier_id}")
async def supplier_account(
    supplier_id: UUID, actor: CurrentPrincipal, use_case: Annotated[GetSupplierAccount, use(GetSupplierAccount)]
) -> AccountOut:
    return AccountOut.model_validate(await use_case(actor, supplier_id))


@router.post("/payments", status_code=status.HTTP_201_CREATED)
async def create_payment(
    body: CreatePaymentIn, actor: CurrentPrincipal, use_case: Annotated[CreatePayment, use(CreatePayment)]
) -> CreatedOut:
    command = CreatePaymentCommand(
        supplier_id=body.supplier_id,
        method=body.method,
        comment=body.comment,
        lines=tuple(NewPaymentLine(line.obligation_id, line.amount) for line in body.lines),
    )
    return CreatedOut(id=await use_case(actor, command))


@router.get("/payments")
async def list_payments(
    actor: CurrentPrincipal,
    use_case: Annotated[ListPayments, use(ListPayments)],
    status_in: Annotated[list[PaymentStatus] | None, Query(alias="status")] = None,
    supplier_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[PaymentListOut]:
    items = await use_case(actor, statuses=set(status_in) if status_in else None, supplier_id=supplier_id, limit=limit)
    return [PaymentListOut.model_validate(item) for item in items]


@router.get("/payments/{payment_id}")
async def get_payment(
    payment_id: UUID, actor: CurrentPrincipal, use_case: Annotated[GetPayment, use(GetPayment)]
) -> PaymentDetailOut:
    return PaymentDetailOut.model_validate(await use_case(actor, payment_id))


@router.post("/payments/{payment_id}/approve", status_code=status.HTTP_204_NO_CONTENT)
async def approve_payment(
    payment_id: UUID, actor: CurrentPrincipal, use_case: Annotated[ApprovePayment, use(ApprovePayment)]
) -> None:
    await use_case(actor, payment_id)


@router.post("/payments/{payment_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_payment(
    payment_id: UUID, body: RejectIn, actor: CurrentPrincipal, use_case: Annotated[RejectPayment, use(RejectPayment)]
) -> None:
    await use_case(actor, payment_id, comment=body.comment)


@router.post("/payments/{payment_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_payment(
    payment_id: UUID, actor: CurrentPrincipal, use_case: Annotated[CancelPayment, use(CancelPayment)]
) -> None:
    await use_case(actor, payment_id)


@router.post("/payments/{payment_id}/pay", status_code=status.HTTP_204_NO_CONTENT)
async def pay_payment(
    payment_id: UUID, body: PayIn, actor: CurrentPrincipal, use_case: Annotated[PayPayment, use(PayPayment)]
) -> None:
    await use_case(actor, payment_id, proof_id=body.proof_id)


@router.post("/attachments", status_code=status.HTTP_201_CREATED)
async def upload_proof(
    request: Request,
    actor: CurrentPrincipal,
    use_case: Annotated[UploadProof, use(UploadProof)],
    content_type: Annotated[str, Header()] = "application/octet-stream",
    content_length: Annotated[int | None, Header()] = None,
) -> CreatedOut:
    """To'lov tasdig'i (chek / ko'chirma): xom tana, `Content-Type: image/jpeg` yoki `application/pdf`."""
    if content_length is not None and content_length > MAX_FILE_BYTES:
        raise InvalidPaymentError("payment.file_size", max_mb=MAX_FILE_BYTES // 1024 // 1024)
    body = await request.body()
    return CreatedOut(id=await use_case(actor, content=body, content_type=content_type.split(";")[0].strip()))


@router.get("/attachments/{file_id}")
async def download_proof(
    file_id: UUID, actor: CurrentPrincipal, use_case: Annotated[GetProof, use(GetProof)]
) -> Response:
    stored = await use_case(actor, file_id)
    return Response(stored.content, media_type=stored.content_type, headers={"Cache-Control": "private, max-age=86400"})
