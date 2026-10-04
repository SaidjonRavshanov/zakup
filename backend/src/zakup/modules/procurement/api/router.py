"""HTTP ↔ use case. Ruxsat va biznes qoidalar — use case / domain'da (ARCHITECTURE §4, §7)."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from zakup.modules.procurement.api.schemas import (
    AddLineIn,
    ApprovedOut,
    ApproveIn,
    CancelOrderIn,
    ChangeLineIn,
    ChooseOfferIn,
    CommentIn,
    CreatedOut,
    CreateRequestIn,
    OrderDetailOut,
    OrderListOut,
    OrderResponseIn,
    PublicOrderOut,
    RequestDetailOut,
    RequestListOut,
    ReviseRequestIn,
    SendOrderIn,
    SentOrderOut,
    StatusOut,
)
from zakup.modules.procurement.application.auto import GenerateAutoRequests
from zakup.modules.procurement.application.orders import (
    ApproveOrderChanges,
    CancelOrder,
    GetOrder,
    GetPublicOrder,
    ListOrders,
    RecordOrderResponse,
    SendOrder,
    SupplierRespond,
)
from zakup.modules.procurement.application.requests import (
    AddRequestLine,
    ApproveRequest,
    CancelRequest,
    ChangeRequestLine,
    ChooseLineOffer,
    CreateRequest,
    GetRequest,
    ListRequests,
    RejectRequest,
    RemoveRequestLine,
    ReturnRequest,
    ReviseRequest,
    SubmitRequest,
)
from zakup.modules.procurement.domain.order import OrderStatus
from zakup.modules.procurement.domain.request import RequestStatus
from zakup.platform.di import Stub
from zakup.platform.security import CurrentPrincipal

router = APIRouter(prefix="/procurement", tags=["procurement"])
# Yetkazuvchi uchun: autentifikatsiyasiz, faqat imzolangan token (ARCHITECTURE §7)
public_router = APIRouter(prefix="/public/orders", tags=["public"])
NO_CONTENT = status.HTTP_204_NO_CONTENT


def use(cls: type) -> Any:
    return Depends(Stub(cls))


# ---------------------------------------------------------------- zayavkalar


@router.get("/requests")
async def list_requests(
    actor: CurrentPrincipal,
    use_case: Annotated[ListRequests, use(ListRequests)],
    status_in: Annotated[list[RequestStatus] | None, Query(alias="status")] = None,
    mine: bool = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[RequestListOut]:
    items = await use_case(actor, statuses=set(status_in) if status_in else None, mine=mine, limit=limit)
    return [RequestListOut.model_validate(item) for item in items]


@router.post("/requests", status_code=status.HTTP_201_CREATED)
async def create_request(
    body: CreateRequestIn, actor: CurrentPrincipal, use_case: Annotated[CreateRequest, use(CreateRequest)]
) -> CreatedOut:
    request_id = await use_case(
        actor, store_id=body.store_id, needed_by=body.needed_by, type=body.type, comment=body.comment
    )
    return CreatedOut(id=request_id)


@router.get("/requests/{request_id}")
async def get_request(
    request_id: UUID, actor: CurrentPrincipal, use_case: Annotated[GetRequest, use(GetRequest)]
) -> RequestDetailOut:
    return RequestDetailOut.model_validate(await use_case(actor, request_id))


@router.patch("/requests/{request_id}", status_code=NO_CONTENT)
async def revise_request(
    request_id: UUID,
    body: ReviseRequestIn,
    actor: CurrentPrincipal,
    use_case: Annotated[ReviseRequest, use(ReviseRequest)],
) -> None:
    await use_case(actor, request_id, needed_by=body.needed_by, comment=body.comment)


@router.post("/requests/{request_id}/lines", status_code=status.HTTP_201_CREATED)
async def add_line(
    request_id: UUID, body: AddLineIn, actor: CurrentPrincipal, use_case: Annotated[AddRequestLine, use(AddRequestLine)]
) -> CreatedOut:
    return CreatedOut(id=await use_case(actor, request_id, product_id=body.product_id, qty=body.qty, note=body.note))


@router.patch("/requests/{request_id}/lines/{line_id}", status_code=NO_CONTENT)
async def change_line(
    request_id: UUID,
    line_id: UUID,
    body: ChangeLineIn,
    actor: CurrentPrincipal,
    use_case: Annotated[ChangeRequestLine, use(ChangeRequestLine)],
) -> None:
    await use_case(actor, request_id, line_id, qty=body.qty, note=body.note)


@router.delete("/requests/{request_id}/lines/{line_id}", status_code=NO_CONTENT)
async def remove_line(
    request_id: UUID,
    line_id: UUID,
    actor: CurrentPrincipal,
    use_case: Annotated[RemoveRequestLine, use(RemoveRequestLine)],
) -> None:
    await use_case(actor, request_id, line_id)


@router.put("/requests/{request_id}/lines/{line_id}/offer", status_code=NO_CONTENT)
async def choose_offer(
    request_id: UUID,
    line_id: UUID,
    body: ChooseOfferIn,
    actor: CurrentPrincipal,
    use_case: Annotated[ChooseLineOffer, use(ChooseLineOffer)],
) -> None:
    await use_case(actor, request_id, line_id, offer_id=body.offer_id)


@router.post("/requests/{request_id}/submit", status_code=NO_CONTENT)
async def submit_request(
    request_id: UUID, actor: CurrentPrincipal, use_case: Annotated[SubmitRequest, use(SubmitRequest)]
) -> None:
    await use_case(actor, request_id)


@router.post("/requests/{request_id}/approve")
async def approve_request(
    request_id: UUID, body: ApproveIn, actor: CurrentPrincipal, use_case: Annotated[ApproveRequest, use(ApproveRequest)]
) -> ApprovedOut:
    line_ids = set(body.line_ids) if body.line_ids is not None else None
    return ApprovedOut(order_ids=await use_case(actor, request_id, line_ids=line_ids))


@router.post("/requests/{request_id}/return", status_code=NO_CONTENT)
async def return_request(
    request_id: UUID, body: CommentIn, actor: CurrentPrincipal, use_case: Annotated[ReturnRequest, use(ReturnRequest)]
) -> None:
    await use_case(actor, request_id, comment=body.comment)


@router.post("/requests/{request_id}/reject", status_code=NO_CONTENT)
async def reject_request(
    request_id: UUID, body: CommentIn, actor: CurrentPrincipal, use_case: Annotated[RejectRequest, use(RejectRequest)]
) -> None:
    await use_case(actor, request_id, comment=body.comment)


@router.post("/requests/{request_id}/cancel", status_code=NO_CONTENT)
async def cancel_request(
    request_id: UUID, actor: CurrentPrincipal, use_case: Annotated[CancelRequest, use(CancelRequest)]
) -> None:
    await use_case(actor, request_id)


# ---------------------------------------------------------------- buyurtmalar


@router.get("/orders")
async def list_orders(
    actor: CurrentPrincipal,
    use_case: Annotated[ListOrders, use(ListOrders)],
    status_in: Annotated[list[OrderStatus] | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[OrderListOut]:
    items = await use_case(actor, statuses=set(status_in) if status_in else None, limit=limit)
    return [OrderListOut.model_validate(item) for item in items]


@router.get("/orders/{order_id}")
async def get_order(
    order_id: UUID, actor: CurrentPrincipal, use_case: Annotated[GetOrder, use(GetOrder)]
) -> OrderDetailOut:
    return OrderDetailOut.model_validate(await use_case(actor, order_id))


@router.post("/orders/{order_id}/send")
async def send_order(
    order_id: UUID, body: SendOrderIn, actor: CurrentPrincipal, use_case: Annotated[SendOrder, use(SendOrder)]
) -> SentOrderOut:
    return SentOrderOut.model_validate(await use_case(actor, order_id, channel=body.channel))


@router.post("/orders/{order_id}/response")
async def record_response(
    order_id: UUID,
    body: OrderResponseIn,
    actor: CurrentPrincipal,
    use_case: Annotated[RecordOrderResponse, use(RecordOrderResponse)],
) -> StatusOut:
    return StatusOut(status=await use_case(actor, order_id, body.to_domain()))


@router.post("/orders/{order_id}/approve-changes")
async def approve_changes(
    order_id: UUID, actor: CurrentPrincipal, use_case: Annotated[ApproveOrderChanges, use(ApproveOrderChanges)]
) -> StatusOut:
    return StatusOut(status=await use_case(actor, order_id))


@router.post("/orders/{order_id}/cancel", status_code=NO_CONTENT)
async def cancel_order(
    order_id: UUID, body: CancelOrderIn, actor: CurrentPrincipal, use_case: Annotated[CancelOrder, use(CancelOrder)]
) -> None:
    await use_case(actor, order_id, reason=body.reason)


# ---------------------------------------------------------------- yetkazuvchi havolasi


@public_router.get("/{token}")
async def public_order(token: str, use_case: Annotated[GetPublicOrder, use(GetPublicOrder)]) -> PublicOrderOut:
    return PublicOrderOut.model_validate(await use_case(token))


@public_router.post("/{token}/response")
async def public_response(
    token: str, body: OrderResponseIn, use_case: Annotated[SupplierRespond, use(SupplierRespond)]
) -> StatusOut:
    return StatusOut(status=await use_case(token, body.to_domain()))


class AutoRequestsIn(BaseModel):
    store_id: UUID | None = None
    force: bool = False  # bugun yaratilgan bo'lsa ham qayta hisoblash


class AutoRequestsOut(BaseModel):
    request_ids: list[UUID]
    lines: int
    skipped: dict[str, int]


@router.post("/auto-requests")
async def generate_auto_requests(
    body: AutoRequestsIn,
    actor: CurrentPrincipal,
    use_case: Annotated[GenerateAutoRequests, use(GenerateAutoRequests)],
) -> AutoRequestsOut:
    """Avto-zayavka qoralamalari (har kuni ertalab worker ham ishga tushiradi)."""
    result = await use_case(actor, store_id=body.store_id, force=body.force)
    return AutoRequestsOut(request_ids=result.request_ids, lines=result.lines, skipped=dict(result.skipped))
