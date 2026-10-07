"""Zayavka use case'lari (WORKFLOW B4, B5). Ruxsat — shu yerda (ARCHITECTURE §7), router'da emas."""

from collections import defaultdict
from dataclasses import replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from zakup.modules.procurement.application.dto import OfferInfo, RequestDetail, RequestLineView, RequestListItem
from zakup.modules.procurement.application.ports import (
    CatalogPort,
    OrderReader,
    OrderRepository,
    RequestReader,
    RequestRepository,
    SupplierCreditPort,
)
from zakup.modules.procurement.domain.approval import ApprovalPolicy, SupplierDebtPolicy, ensure_supplier_credit
from zakup.modules.procurement.domain.order import NewOrderLine, PurchaseOrder
from zakup.modules.procurement.domain.request import (
    InvalidRequestError,
    LineDecision,
    OfferChoice,
    PurchaseRequest,
    RequestStatus,
    RequestType,
)
from zakup.shared_kernel.auth import Principal, Role
from zakup.shared_kernel.clock import Clock, business_today, utc_now
from zakup.shared_kernel.errors import NotFoundError
from zakup.shared_kernel.uow import UnitOfWork

CREATORS = (Role.INITIATOR, Role.BUYER, Role.ADMIN)
MANAGERS = (Role.BUYER, Role.ADMIN)
DECIDERS = (Role.BUYER, Role.APPROVER, Role.ADMIN)
# Hamma zayavkalarni ko'radiganlar (o'z omborlari bo'yicha); qolganlar — faqat o'zinikini
OVERSEERS = (Role.BUYER, Role.APPROVER, Role.ADMIN, Role.AUDITOR, Role.ACCOUNTANT)


def _choice(offer: OfferInfo) -> OfferChoice:
    return OfferChoice(offer_id=offer.offer_id, supplier_id=offer.supplier_id, price_per_base=offer.price_per_base)


async def _load(requests: RequestRepository, request_id: UUID) -> PurchaseRequest:
    request = await requests.get(request_id)
    if request is None:
        raise NotFoundError("request.not_found")
    return request


def _ensure_can_edit(actor: Principal, request: PurchaseRequest) -> None:
    """Qoralamani tashabbuskorning o'zi yoki ombor zakupshigi / admin tahrirlaydi."""
    if actor.user_id != request.initiator_id:
        actor.require(*MANAGERS, store_id=request.store_id)


def _ensure_can_view(actor: Principal, request_store: UUID, initiator_id: UUID) -> None:
    if actor.user_id != initiator_id:
        actor.require(*OVERSEERS, store_id=request_store)


class CreateRequest:
    def __init__(
        self, uow: UnitOfWork, requests: RequestRepository, catalog: CatalogPort, clock: Clock = utc_now
    ) -> None:
        self._uow = uow
        self._requests = requests
        self._catalog = catalog
        self._clock = clock

    async def __call__(
        self,
        actor: Principal,
        *,
        store_id: UUID,
        needed_by: date,
        type: RequestType,  # noqa: A002 — domen atamasi
        comment: str | None,
    ) -> UUID:
        actor.require(*CREATORS, store_id=store_id)
        if type is RequestType.AUTO:
            raise InvalidRequestError("request.auto_is_system")
        async with self._uow:
            if not await self._catalog.store_available(store_id):
                raise NotFoundError("store.not_found")
            request = PurchaseRequest.create(
                number=await self._requests.next_number(),
                store_id=store_id,
                initiator=actor,
                needed_by=needed_by,
                today=business_today(self._clock),
                type=type,
                comment=comment,
            )
            await self._requests.add(request)
            await self._uow.commit()
            return request.id


class ReviseRequest:
    def __init__(self, uow: UnitOfWork, requests: RequestRepository, clock: Clock = utc_now) -> None:
        self._uow = uow
        self._requests = requests
        self._clock = clock

    async def __call__(self, actor: Principal, request_id: UUID, *, needed_by: date, comment: str | None) -> None:
        async with self._uow:
            request = await _load(self._requests, request_id)
            _ensure_can_edit(actor, request)
            request.revise(needed_by=needed_by, comment=comment, today=business_today(self._clock))
            await self._requests.save(request)
            await self._uow.commit()


class AddRequestLine:
    """Pozitsiya qo'shiladi; yetkazuvchi avtomatik taklif qilinadi (kartochka → eng arzon),
    keyin o'zgartirish mumkin."""

    def __init__(self, uow: UnitOfWork, requests: RequestRepository, catalog: CatalogPort) -> None:
        self._uow = uow
        self._requests = requests
        self._catalog = catalog

    async def __call__(
        self, actor: Principal, request_id: UUID, *, product_id: UUID, qty: Decimal, note: str | None
    ) -> UUID:
        async with self._uow:
            request = await _load(self._requests, request_id)
            _ensure_can_edit(actor, request)
            if not await self._catalog.product_available(product_id):
                raise NotFoundError("product.not_found")
            offer = await self._catalog.default_offer(product_id, request.store_id)
            line = request.add_line(product_id=product_id, qty=qty, note=note, offer=_choice(offer) if offer else None)
            await self._requests.save(request)
            await self._uow.commit()
            return line.id


class ChangeRequestLine:
    def __init__(self, uow: UnitOfWork, requests: RequestRepository) -> None:
        self._uow = uow
        self._requests = requests

    async def __call__(
        self, actor: Principal, request_id: UUID, line_id: UUID, *, qty: Decimal, note: str | None
    ) -> None:
        async with self._uow:
            request = await _load(self._requests, request_id)
            _ensure_can_edit(actor, request)
            request.change_line(line_id, qty=qty, note=note)
            await self._requests.save(request)
            await self._uow.commit()


class RemoveRequestLine:
    def __init__(self, uow: UnitOfWork, requests: RequestRepository) -> None:
        self._uow = uow
        self._requests = requests

    async def __call__(self, actor: Principal, request_id: UUID, line_id: UUID) -> None:
        async with self._uow:
            request = await _load(self._requests, request_id)
            _ensure_can_edit(actor, request)
            request.remove_line(line_id)
            await self._requests.save(request)
            await self._uow.commit()


class ChooseLineOffer:
    """Yetkazuvchini tanlash: qoralamada — tahrirlovchi, tasdiqlashda — faqat zakupshik/admin (WORKFLOW B6)."""

    def __init__(self, uow: UnitOfWork, requests: RequestRepository, catalog: CatalogPort) -> None:
        self._uow = uow
        self._requests = requests
        self._catalog = catalog

    async def __call__(self, actor: Principal, request_id: UUID, line_id: UUID, *, offer_id: UUID | None) -> None:
        async with self._uow:
            request = await _load(self._requests, request_id)
            if request.status is RequestStatus.DRAFT:
                _ensure_can_edit(actor, request)
            else:
                actor.require(*MANAGERS, store_id=request.store_id)
            choice = None
            if offer_id is not None:
                offer = await self._catalog.offer(offer_id)
                line = next((ln for ln in request.lines if ln.id == line_id), None)
                if offer is None or not offer.available or (line is not None and offer.product_id != line.product_id):
                    raise InvalidRequestError("request.offer_mismatch")
                choice = _choice(offer)
            request.choose_offer(line_id, choice)
            await self._requests.save(request)
            await self._uow.commit()


class SubmitRequest:
    def __init__(self, uow: UnitOfWork, requests: RequestRepository, clock: Clock = utc_now) -> None:
        self._uow = uow
        self._requests = requests
        self._clock = clock

    async def __call__(self, actor: Principal, request_id: UUID) -> None:
        async with self._uow:
            request = await _load(self._requests, request_id)
            _ensure_can_edit(actor, request)
            request.submit(today=business_today(self._clock), at=self._clock())
            await self._requests.save(request)
            self._uow.track(request)
            await self._uow.commit()


class ApproveRequest:
    """Tasdiqlash + darhol PO'larga bo'lish: bitta PO = yetkazuvchi + ombor + sana (WORKFLOW B6.1)."""

    def __init__(
        self,
        uow: UnitOfWork,
        requests: RequestRepository,
        orders: OrderRepository,
        catalog: CatalogPort,
        *,
        policy: ApprovalPolicy,
        credit: SupplierCreditPort | None = None,
        debt_policy: SupplierDebtPolicy = SupplierDebtPolicy.REQUIRE_ADMIN,
        clock: Clock = utc_now,
    ) -> None:
        self._uow = uow
        self._requests = requests
        self._orders = orders
        self._catalog = catalog
        self._policy = policy
        self._credit = credit
        self._debt_policy = debt_policy
        self._clock = clock

    async def __call__(self, actor: Principal, request_id: UUID, *, line_ids: set[UUID] | None = None) -> list[UUID]:
        async with self._uow:
            request = await _load(self._requests, request_id)
            actor.require(*DECIDERS, store_id=request.store_id)
            request.approve(actor, self._policy, at=self._clock(), line_ids=line_ids)
            order_ids = await self._split(request, actor)
            request.mark_split()
            await self._requests.save(request)
            self._uow.track(request)
            await self._uow.commit()
            return order_ids

    async def _split(self, request: PurchaseRequest, actor: Principal) -> list[UUID]:
        by_supplier: dict[UUID, list[NewOrderLine]] = defaultdict(list)
        for line in request.approved_lines:
            assert line.offer is not None  # approve() tekshirgan
            offer = await self._catalog.offer(line.offer.offer_id)
            packs = await self._catalog.pack_quantity(line.offer.offer_id, line.qty)
            if offer is None or packs is None or not offer.available:
                raise InvalidRequestError("request.offer_unavailable")
            by_supplier[offer.supplier_id].append(
                NewOrderLine(
                    request_line_id=line.id,
                    product_id=line.product_id,
                    offer_id=offer.offer_id,
                    pack_unit=offer.pack_unit,
                    pack_factor=offer.pack_factor,
                    qty_packs=packs,
                    price_per_pack=offer.price_per_pack,
                )
            )
        order_ids = []
        for supplier_id, lines in by_supplier.items():
            amount = sum((ln.qty_packs * ln.price_per_pack for ln in lines), Decimal(0))
            await self._check_credit(actor, supplier_id, amount)
            order = PurchaseOrder.create(
                number=await self._orders.next_number(),
                request_id=request.id,
                supplier_id=supplier_id,
                store_id=request.store_id,
                delivery_date=request.needed_by,
                lines=lines,
            )
            await self._orders.add(order)
            order_ids.append(order.id)
        return order_ids

    async def _check_credit(self, actor: Principal, supplier_id: UUID, amount: Decimal) -> None:
        if self._credit is None:
            return
        reason = await self._credit.check(supplier_id, amount)
        if reason is not None:
            supplier = await self._catalog.supplier(supplier_id)
            ensure_supplier_credit(actor, reason, self._debt_policy, supplier=supplier.name if supplier else "?")


class ReturnRequest:
    def __init__(self, uow: UnitOfWork, requests: RequestRepository, clock: Clock = utc_now) -> None:
        self._uow = uow
        self._requests = requests
        self._clock = clock

    async def __call__(self, actor: Principal, request_id: UUID, *, comment: str) -> None:
        async with self._uow:
            request = await _load(self._requests, request_id)
            actor.require(*DECIDERS, store_id=request.store_id)
            request.return_to_draft(actor, comment=comment, at=self._clock())
            await self._requests.save(request)
            self._uow.track(request)
            await self._uow.commit()


class RejectRequest:
    def __init__(self, uow: UnitOfWork, requests: RequestRepository, clock: Clock = utc_now) -> None:
        self._uow = uow
        self._requests = requests
        self._clock = clock

    async def __call__(self, actor: Principal, request_id: UUID, *, comment: str) -> None:
        async with self._uow:
            request = await _load(self._requests, request_id)
            actor.require(*DECIDERS, store_id=request.store_id)
            request.reject(actor, comment=comment, at=self._clock())
            await self._requests.save(request)
            self._uow.track(request)
            await self._uow.commit()


class CancelRequest:
    def __init__(self, uow: UnitOfWork, requests: RequestRepository) -> None:
        self._uow = uow
        self._requests = requests

    async def __call__(self, actor: Principal, request_id: UUID) -> None:
        async with self._uow:
            request = await _load(self._requests, request_id)
            _ensure_can_edit(actor, request)
            request.cancel()
            await self._requests.save(request)
            await self._uow.commit()


class ListRequests:
    def __init__(self, reader: RequestReader, catalog: CatalogPort) -> None:
        self._reader = reader
        self._catalog = catalog

    async def __call__(
        self, actor: Principal, *, statuses: set[RequestStatus] | None = None, mine: bool = False, limit: int = 100
    ) -> list[RequestListItem]:
        sees_all = actor.has_role(*OVERSEERS)
        stores = scoped_stores(actor, OVERSEERS)
        items = await self._reader.list(
            statuses=statuses,
            store_ids=stores if sees_all and not mine else None,
            initiator_id=None if sees_all and not mine else actor.user_id,
            limit=max(1, min(limit, 200)),
        )
        labels = await self._catalog.labels(stores={item.store_id for item in items})
        return [replace(item, store_name=labels.stores.get(item.store_id)) for item in items]


class GetRequest:
    def __init__(self, reader: RequestReader, orders: OrderReader, catalog: CatalogPort) -> None:
        self._reader = reader
        self._orders = orders
        self._catalog = catalog

    async def __call__(self, actor: Principal, request_id: UUID) -> RequestDetail:
        detail = await self._reader.detail(request_id)
        if detail is None:
            raise NotFoundError("request.not_found")
        _ensure_can_view(actor, detail.store_id, detail.initiator_id)
        orders = await self._orders.list(statuses=None, store_ids=None, request_id=request_id, limit=50)
        labels = await self._catalog.labels(
            products={line.product_id for line in detail.lines},
            suppliers={line.supplier_id for line in detail.lines if line.supplier_id}
            | {order.supplier_id for order in orders},
            stores={detail.store_id},
        )
        lines = tuple(
            [
                replace(
                    await self._packed(line),
                    product_name=labels.product(line.product_id)[0],
                    base_unit=labels.product(line.product_id)[1],
                    supplier_name=labels.suppliers.get(line.supplier_id) if line.supplier_id else None,
                )
                for line in detail.lines
            ]
        )
        priced = [ln for ln in lines if ln.decision != LineDecision.REJECTED and ln.price_per_base is not None]
        order_total = sum((ln.order_amount if ln.order_amount is not None else ln.amount for ln in priced), Decimal(0))
        return replace(
            detail,
            lines=lines,
            order_total=order_total,
            store_name=labels.stores.get(detail.store_id),
            orders=tuple(
                replace(
                    order,
                    supplier_name=labels.suppliers.get(order.supplier_id),
                    store_name=labels.stores.get(order.store_id),
                )
                for order in orders
            ),
        )

    async def _packed(self, line: RequestLineView) -> RequestLineView:
        """Qator → buyurtmadagi qadoqlar va summa (ApproveRequest._split bilan bir xil hisob)."""
        if line.offer_id is None:
            return line
        offer = await self._catalog.offer(line.offer_id)
        packs = await self._catalog.pack_quantity(line.offer_id, line.qty)
        if offer is None or packs is None:
            return line
        return replace(
            line,
            pack_unit=offer.pack_unit,
            pack_factor=offer.pack_factor,
            qty_packs=packs,
            order_amount=(packs * offer.price_per_pack).quantize(Decimal("0.01"), ROUND_HALF_UP),
        )


def scoped_stores(actor: Principal, roles: tuple[Role, ...]) -> set[UUID] | None:
    """None — barcha omborlar (rol omborsiz berilgan); aks holda rol berilgan omborlar."""
    grants = [grant for grant in actor.grants if grant.role in roles]
    if any(grant.store_id is None for grant in grants):
        return None
    return {grant.store_id for grant in grants if grant.store_id is not None}
