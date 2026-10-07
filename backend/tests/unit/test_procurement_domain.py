from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from zakup.modules.procurement.application.dto import OrderDetail, OrderLineView
from zakup.modules.procurement.application.message import order_message
from zakup.modules.procurement.domain.approval import ApprovalLimitError, ApprovalPolicy
from zakup.modules.procurement.domain.order import (
    Channel,
    LineResponse,
    NewOrderLine,
    OrderStatus,
    PurchaseOrder,
    ResponseKind,
    Tolerance,
)
from zakup.modules.procurement.domain.request import (
    InvalidRequestError,
    LineDecision,
    OfferChoice,
    PurchaseRequest,
    RequestStatus,
)
from zakup.shared_kernel.auth import Principal, Role, RoleGrant
from zakup.shared_kernel.errors import InvalidTransitionError
from zakup.shared_kernel.ids import new_id

TODAY = date(2026, 10, 4)
NOW = datetime(2026, 10, 4, 9, tzinfo=UTC)
STORE = new_id()


def _actor(*roles: Role, store: UUID | None = None) -> Principal:
    return Principal(user_id=new_id(), grants=frozenset(RoleGrant(role, store) for role in roles))


def _offer(price_per_base: str = "10000") -> OfferChoice:
    return OfferChoice(offer_id=new_id(), supplier_id=new_id(), price_per_base=Decimal(price_per_base))


def _request(chef: Principal | None = None) -> PurchaseRequest:
    return PurchaseRequest.create(
        number="Z-000001",
        store_id=STORE,
        initiator=chef or _actor(Role.INITIATOR),
        needed_by=date(2026, 10, 6),
        today=TODAY,
    )


def test_request_lifecycle_and_totals() -> None:
    request = _request()
    request.add_line(product_id=new_id(), qty=Decimal(30), note=None, offer=_offer("10000"))
    request.add_line(product_id=new_id(), qty=Decimal("2.5"), note="банкет", offer=_offer("4000"))
    assert request.total == Decimal(310000)

    request.submit(today=TODAY, at=NOW)
    assert (request.status, request.submitted_at) == (RequestStatus.PENDING_APPROVAL, NOW)
    with pytest.raises(InvalidTransitionError):
        request.add_line(product_id=new_id(), qty=Decimal(1), note=None, offer=None)

    request.approve(_actor(Role.BUYER), ApprovalPolicy(), at=NOW)
    assert request.status is RequestStatus.APPROVED
    request.mark_split()
    assert request.status is RequestStatus.SPLIT


def test_validation_rules() -> None:
    request = _request()
    product = new_id()
    request.add_line(product_id=product, qty=Decimal(1), note=None, offer=None)
    with pytest.raises(InvalidRequestError):
        request.add_line(product_id=product, qty=Decimal(1), note=None, offer=None)  # bitta tovar — bitta qator
    with pytest.raises(InvalidRequestError):
        request.add_line(product_id=new_id(), qty=Decimal(0), note=None, offer=None)
    with pytest.raises(InvalidRequestError):
        _request().submit(today=TODAY, at=NOW)  # bo'sh
    with pytest.raises(InvalidRequestError):
        PurchaseRequest.create(
            number="Z-2", store_id=STORE, initiator=_actor(Role.INITIATOR), needed_by=date(2026, 10, 1), today=TODAY
        )


def test_line_without_supplier_cannot_be_approved() -> None:
    request = _request()
    request.add_line(product_id=new_id(), qty=Decimal(1), note=None, offer=None)
    request.submit(today=TODAY, at=NOW)
    with pytest.raises(InvalidRequestError):
        request.approve(_actor(Role.ADMIN), ApprovalPolicy(), at=NOW)


def test_partial_approval_rejects_the_rest() -> None:
    request = _request()
    keep = request.add_line(product_id=new_id(), qty=Decimal(1), note=None, offer=_offer())
    drop = request.add_line(product_id=new_id(), qty=Decimal(1), note=None, offer=_offer())
    request.submit(today=TODAY, at=NOW)
    request.approve(_actor(Role.BUYER), ApprovalPolicy(), at=NOW, line_ids={keep.id})
    assert request.status is RequestStatus.PARTIALLY_APPROVED
    assert (keep.decision, drop.decision) == (LineDecision.APPROVED, LineDecision.REJECTED)
    assert request.approved_lines == [keep]


@pytest.mark.parametrize(
    ("roles", "amount", "allowed"),
    [
        ((Role.BUYER,), "2000000", True),
        ((Role.BUYER,), "2000001", False),
        ((Role.APPROVER,), "9000000", True),
        ((Role.BUYER, Role.APPROVER), "10000000", True),
        ((Role.APPROVER,), "10000001", False),
        ((Role.ADMIN,), "999999999", True),
        ((Role.INITIATOR,), "1", False),
    ],
)
def test_approval_matrix(roles: tuple[Role, ...], amount: str, allowed: bool) -> None:
    policy = ApprovalPolicy()
    actor = _actor(*roles)
    if allowed:
        policy.ensure_can_approve(actor, STORE, Decimal(amount))
    else:
        with pytest.raises(ApprovalLimitError):
            policy.ensure_can_approve(actor, STORE, Decimal(amount))


def test_limit_applies_only_in_granted_store() -> None:
    buyer_elsewhere = _actor(Role.BUYER, store=new_id())
    with pytest.raises(ApprovalLimitError):
        ApprovalPolicy().ensure_can_approve(buyer_elsewhere, STORE, Decimal(1))


def test_self_approval_is_flagged_as_role_conflict() -> None:
    chef_buyer = _actor(Role.INITIATOR, Role.BUYER)
    request = _request(chef_buyer)
    request.add_line(product_id=new_id(), qty=Decimal(1), note=None, offer=_offer())
    request.submit(today=TODAY, at=NOW)
    request.approve(chef_buyer, ApprovalPolicy(), at=NOW)
    (record,) = request.pull_new_approvals()
    assert record.role_conflict


def test_return_requires_comment_and_goes_back_to_draft() -> None:
    request = _request()
    request.add_line(product_id=new_id(), qty=Decimal(1), note=None, offer=_offer())
    request.submit(today=TODAY, at=NOW)
    with pytest.raises(InvalidRequestError):
        request.return_to_draft(_actor(Role.APPROVER), comment="  ", at=NOW)
    request.return_to_draft(_actor(Role.APPROVER), comment="Ko'p, 20 kg yetadi", at=NOW)
    assert request.status is RequestStatus.DRAFT
    request.change_line(request.lines[0].id, qty=Decimal(20), note=None)


# ---------------------------------------------------------------- PO


def _order(price: str = "250000", packs: str = "2") -> PurchaseOrder:
    return PurchaseOrder.create(
        number="PO-000001",
        request_id=None,
        supplier_id=new_id(),
        store_id=STORE,
        delivery_date=date(2026, 10, 6),
        lines=[
            NewOrderLine(
                request_line_id=None,
                product_id=new_id(),
                offer_id=new_id(),
                pack_unit="bag",
                pack_factor=Decimal(25),
                qty_packs=Decimal(packs),
                price_per_pack=Decimal(price),
            )
        ],
    )


def _sent(order: PurchaseOrder) -> PurchaseOrder:
    order.send(by=new_id(), channel=Channel.TELEGRAM, at=NOW, deadline=NOW)
    return order


@pytest.mark.parametrize(
    ("response", "status"),
    [
        (LineResponse(ResponseKind.CONFIRMED), OrderStatus.CONFIRMED),
        (LineResponse(ResponseKind.PRICE_CHANGED, price_per_pack=Decimal(257000)), OrderStatus.CONFIRMED),  # +2.8%
        (LineResponse(ResponseKind.PRICE_CHANGED, price_per_pack=Decimal(260000)), OrderStatus.REAPPROVAL),  # +4%
        (LineResponse(ResponseKind.QTY_CHANGED, qty_packs=Decimal(1)), OrderStatus.PARTIALLY_CONFIRMED),
        # Ko'paytirish (ochiq havoladan ham) — tasdiqlanmagan xarid: qayta tasdiqlash
        (LineResponse(ResponseKind.QTY_CHANGED, qty_packs=Decimal(200)), OrderStatus.REAPPROVAL),
        (LineResponse(ResponseKind.OUT_OF_STOCK), OrderStatus.CANCELLED),
    ],
)
def test_supplier_response_status(response: LineResponse, status: OrderStatus) -> None:
    order = _sent(_order())
    order.record_response({order.lines[0].id: response}, Tolerance(), at=NOW)
    assert order.status is status


def test_reapproval_then_confirmed_with_new_price() -> None:
    order = _sent(_order())
    order.record_response(
        {order.lines[0].id: LineResponse(ResponseKind.PRICE_CHANGED, price_per_pack=Decimal(300000))},
        Tolerance(),
        at=NOW,
    )
    assert order.status is OrderStatus.REAPPROVAL
    order.approve_changes()
    assert (order.status, order.confirmed_total) == (OrderStatus.CONFIRMED, Decimal(600000))


def test_absolute_tolerance_limits_small_percentages() -> None:
    order = _sent(_order(packs="100"))
    tolerance = Tolerance(price_pct=Decimal(3), abs_max=Decimal(100000))
    order.record_response(
        {order.lines[0].id: LineResponse(ResponseKind.PRICE_CHANGED, price_per_pack=Decimal(252000))}, tolerance, at=NOW
    )  # +0.8%, lekin 100 qop x 2000 = 200 000 so'm > 100 000
    assert order.status is OrderStatus.REAPPROVAL


def test_response_only_after_sending() -> None:
    order = _order()
    with pytest.raises(InvalidTransitionError):
        order.record_response({}, Tolerance(), at=NOW)


def test_order_message_uses_supplier_units() -> None:
    detail = OrderDetail(
        id=new_id(),
        number="PO-000045",
        request_id=None,
        supplier_id=new_id(),
        store_id=STORE,
        delivery_date=date(2026, 10, 6),
        status=OrderStatus.SENT,
        total=Decimal(500000),
        confirmed_total=Decimal(500000),
        sent_at=NOW,
        sent_channel=Channel.TELEGRAM,
        response_deadline=None,
        responded_at=None,
        cancel_reason=None,
        created_at=NOW,
        version=1,
        store_name="Главный склад",
        lines=(
            OrderLineView(
                id=new_id(),
                product_id=new_id(),
                offer_id=new_id(),
                pack_unit="bag",
                pack_factor=Decimal(25),
                qty_packs=Decimal(2),
                price_per_pack=Decimal(250000),
                amount=Decimal(500000),
                response=None,
                qty_confirmed=None,
                price_confirmed=None,
                needs_reapproval=False,
                product_name="Мука высший сорт",
                base_unit="kg",
            ),
        ),
    )
    text = order_message(detail, url="https://x/s/abc", company="Tarnov")
    assert "Заказ PO-000045 — Tarnov" in text
    assert "1. Мука высший сорт — 2 меш (50 кг) × 250 000 = 500 000 сум" in text
    assert text.endswith("https://x/s/abc")


def test_confirmed_order_can_be_cancelled_until_received() -> None:
    order = _sent(_order())
    order.record_response({}, Tolerance(), at=NOW)
    assert order.status is OrderStatus.CONFIRMED
    order.cancel(reason="Yetkazuvchi kelmadi")
    assert order.status is OrderStatus.CANCELLED


def test_approving_changes_emits_event() -> None:
    order = _sent(_order())
    order.record_response(
        {order.lines[0].id: LineResponse(ResponseKind.QTY_CHANGED, qty_packs=Decimal(3))}, Tolerance(), at=NOW
    )
    assert order.status is OrderStatus.REAPPROVAL
    order.pull_events()
    order.approve_changes()
    (event,) = order.pull_events()
    assert (event.event_type, order.status) == ("procurement.order_changes_approved", OrderStatus.CONFIRMED)


def test_request_amount_is_rounded_to_supplier_packs() -> None:
    offer = OfferChoice(
        new_id(),
        new_id(),
        Decimal(10000),
        pack_unit="bag",
        pack_factor=Decimal(25),
        pack_multiple=Decimal(2),
        price_per_pack=Decimal(250000),
    )
    assert offer.packs(Decimal(1)) == Decimal(2)  # 1 kg → 1 qop → karralilik 2
    assert offer.packs(Decimal(51)) == Decimal(4)
    legacy = OfferChoice(new_id(), new_id(), Decimal(10000))
    assert legacy.packs(Decimal(1)) is None  # eski qator: bazaviy narx bo'yicha
