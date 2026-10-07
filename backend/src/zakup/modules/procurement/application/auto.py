"""Avto-zayavka (WORKFLOW B3, B4a): har bir ombor uchun QORALAMA, buyurtma emas.

Har pozitsiya yonida "nega shuncha": sarf, qoldiq, yo'lda, formula — `calc` (zakupshik va tasdiqlovchi ko'radi).
Trigger: qoldiq + yo'lda buyurtma nuqtasidan past YOKI bugun yetkazuvchining buyurtma kuni (va ehtiyoj bor).
Ochiq zayavkada (qoralama / tasdiqlashda) turgan tovar qayta taklif qilinmaydi.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import structlog

from zakup.modules.planning.application.facade import DemandInputs, DemandResult, calculate
from zakup.modules.procurement.application.dto import AutoCardInfo, DemandSnapshot, OfferInfo, SupplierInfo
from zakup.modules.procurement.application.ports import CatalogPort, DemandPort, OrderRepository, RequestRepository
from zakup.modules.procurement.application.requests import offer_choice
from zakup.modules.procurement.domain.request import PurchaseRequest, Suggestion
from zakup.shared_kernel.auth import SYSTEM_USER_ID, Principal, Role
from zakup.shared_kernel.clock import Clock, business_today, utc_now
from zakup.shared_kernel.uow import UnitOfWork

log = structlog.get_logger()
RUNNERS = (Role.BUYER, Role.ADMIN)


@dataclass(slots=True)
class AutoRunResult:
    request_ids: list[UUID] = field(default_factory=list)
    lines: int = 0
    skipped: Counter[str] = field(default_factory=Counter)


@dataclass(frozen=True, slots=True)
class _Proposal:
    product_id: UUID
    qty: Decimal
    needed_by: date
    offer: OfferInfo
    suggestion: Suggestion


def _stores_in_scope(actor: Principal | None) -> set[UUID] | None:
    if actor is None:
        return None
    grants = [g for g in actor.grants if g.role in RUNNERS]
    if any(g.store_id is None for g in grants):
        return None
    return {g.store_id for g in grants if g.store_id}


class GenerateAutoRequests:
    def __init__(
        self,
        uow: UnitOfWork,
        requests: RequestRepository,
        orders: OrderRepository,
        catalog: CatalogPort,
        *,
        demand: DemandPort,
        clock: Clock = utc_now,
    ) -> None:
        self._uow = uow
        self._requests = requests
        self._orders = orders
        self._catalog = catalog
        self._demand = demand
        self._clock = clock

    async def __call__(
        self, actor: Principal | None, *, store_id: UUID | None = None, force: bool = False
    ) -> AutoRunResult:
        """actor=None — rejalashtirilgan ishga tushirish (worker). force — bugun yaratilgan bo'lsa ham qayta."""
        if actor is not None:
            actor.require(*RUNNERS, store_id=store_id)
        scope = _stores_in_scope(actor)
        today = business_today(self._clock)
        result = AutoRunResult()
        async with self._uow:
            by_store: dict[UUID, list[AutoCardInfo]] = defaultdict(list)
            for card in await self._catalog.auto_cards(store_id):
                if scope is None or card.store_id in scope:
                    by_store[card.store_id].append(card)
            for store, cards in by_store.items():
                if not force and await self._requests.has_auto_on(store, today):
                    result.skipped["already_today"] += 1
                    continue
                proposals = await self._propose(store, cards, today, result.skipped)
                for needed_by, group in _by_date(proposals).items():
                    request = PurchaseRequest.create_auto(
                        number=await self._requests.next_number(),
                        store_id=store,
                        initiator_id=SYSTEM_USER_ID,
                        needed_by=needed_by,
                        today=today,
                    )
                    for p in group:
                        request.add_auto_line(
                            product_id=p.product_id,
                            qty=p.qty,
                            offer=offer_choice(p.offer),
                            suggestion=p.suggestion,
                        )
                    request.mark_drafted()
                    await self._requests.add(request)
                    self._uow.track(request)
                    result.request_ids.append(request.id)
                    result.lines += len(group)
            await self._uow.commit()
        log.info("auto_requests_done", requests=len(result.request_ids), lines=result.lines, **result.skipped)
        return result

    async def _propose(
        self, store: UUID, cards: list[AutoCardInfo], today: date, skipped: Counter[str]
    ) -> list[_Proposal]:
        products = [card.product_id for card in cards]
        busy = await self._requests.open_products(store)
        stats = await self._demand.stats(store, products, today=today)
        transit = await self._orders.in_transit(store, products)
        proposals = []
        for card in cards:
            if card.product_id in busy:
                skipped["in_open_request"] += 1
                continue
            offer = await self._catalog.default_offer(card.product_id, store)
            supplier = await self._catalog.supplier(offer.supplier_id) if offer and offer.available else None
            if offer is None or supplier is None:
                skipped["no_offer"] += 1
                continue
            snapshot = stats.get(card.product_id)
            if snapshot is None or snapshot.days_observed == 0:
                skipped["no_history"] += 1
                continue
            proposal = await self._proposal(
                card,
                offer=offer,
                supplier=supplier,
                snapshot=snapshot,
                in_transit=transit.get(card.product_id),
                today=today,
            )
            if proposal is None:
                skipped["enough_stock"] += 1
                continue
            proposals.append(proposal)
        return proposals

    async def _proposal(
        self,
        card: AutoCardInfo,
        *,
        offer: OfferInfo,
        supplier: SupplierInfo,
        snapshot: DemandSnapshot,
        in_transit: Decimal | None,
        today: date,
    ) -> _Proposal | None:
        lead = supplier.lead_time_days
        coverage = card.coverage_days
        if card.shelf_life_days is not None:  # tez buziladigan: qoplash ≤ yaroqlilik - yetkazish (WORKFLOW B3)
            coverage = max(min(coverage, card.shelf_life_days - lead), 1)
        demand = calculate(
            DemandInputs(
                avg_daily=snapshot.avg_daily,
                stock=snapshot.stock or Decimal(0),
                in_transit=in_transit or Decimal(0),
                lead_days=lead,
                coverage_days=coverage,
                safety_stock=card.safety_stock,
                seasonal_factor=card.seasonal_factor,
            )
        )
        order_day = today.isoweekday() in supplier.order_weekdays
        if demand.need <= 0 or not (demand.below_reorder_point or order_day):
            return None
        packs = await self._catalog.pack_quantity(offer.offer_id, demand.need)
        if packs is None or packs <= 0:
            return None
        qty = packs * offer.pack_factor
        return _Proposal(
            product_id=card.product_id,
            qty=qty,
            needed_by=today + timedelta(days=max(lead, 1)),
            offer=offer,
            suggestion=Suggestion(
                qty=qty,
                calc=_explain(
                    demand,
                    snapshot=snapshot,
                    card=card,
                    offer=offer,
                    in_transit=in_transit,
                    lead=lead,
                    coverage=coverage,
                    packs=packs,
                    order_day=order_day,
                ),
            ),
        )


def _by_date(proposals: list[_Proposal]) -> dict[date, list[_Proposal]]:
    groups: dict[date, list[_Proposal]] = defaultdict(list)
    for proposal in proposals:
        groups[proposal.needed_by].append(proposal)
    return dict(sorted(groups.items()))


def _explain(
    demand: DemandResult,
    *,
    snapshot: DemandSnapshot,
    card: AutoCardInfo,
    offer: OfferInfo,
    in_transit: Decimal | None,
    lead: int,
    coverage: int,
    packs: Decimal,
    order_day: bool,
) -> dict[str, str | None]:
    return {
        "avg_daily": str(demand.daily),
        "window_days": str(snapshot.window_days),
        "days_observed": str(snapshot.days_observed),
        "stock": str(snapshot.stock) if snapshot.stock is not None else None,
        "stock_at": snapshot.stock_at.isoformat() if snapshot.stock_at else None,
        "in_transit": str(in_transit or 0),
        "lead_days": str(lead),
        "coverage_days": str(coverage),
        "safety_stock": str(card.safety_stock),
        "seasonal_factor": str(card.seasonal_factor),
        "target": str(demand.target),
        "reorder_point": str(demand.reorder_point),
        "need": str(demand.need),
        "packs": str(packs),
        "pack_unit": offer.pack_unit,
        "pack_factor": str(offer.pack_factor),
        "trigger": "reorder_point" if demand.below_reorder_point else "order_day" if order_day else None,
    }
