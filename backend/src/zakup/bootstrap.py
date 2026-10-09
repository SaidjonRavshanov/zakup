"""Composition root: barcha implementatsiyalar port'larga **faqat shu yerda** ulanadi (ARCHITECTURE §4).

Yangi modul qo'shish: router'ni `ROUTERS` ga, provider'larni `_wire_*` ga qo'shing.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any, Protocol, TypeVar
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, FastAPI
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from zakup.modules.analytics.api.router import router as analytics_router
from zakup.modules.analytics.application.reports import Reports
from zakup.modules.analytics.infrastructure.readers import SqlAnalyticsReader
from zakup.modules.catalog.api.router import router as catalog_router
from zakup.modules.catalog.application.iiko_sync import IikoCatalogSync
from zakup.modules.catalog.application.offers import AddOffer, ArchiveOffer, GetPriceHistory, ReviseOffer
from zakup.modules.catalog.application.products import (
    ArchiveProduct,
    CreateCategory,
    GetProduct,
    ListCategories,
    ListProducts,
    RegisterProduct,
    ReviseProduct,
)
from zakup.modules.catalog.application.purchase_cards import ConfigurePurchaseCard
from zakup.modules.catalog.application.queries import CatalogQueries
from zakup.modules.catalog.application.stores import ArchiveStore, ListStores, RegisterStore, ReviseStore
from zakup.modules.catalog.application.use_cases import (
    ArchiveSupplier,
    GetSupplier,
    ListSuppliers,
    RegisterSupplier,
    ReviseSupplier,
)
from zakup.modules.catalog.infrastructure.readers import (
    SqlCategoryReader,
    SqlLabelReader,
    SqlOffersByProduct,
    SqlPriceHistoryReader,
    SqlProductReader,
    SqlStoreReader,
    SqlSupplierReader,
)
from zakup.modules.catalog.infrastructure.repositories import (
    SqlBranchRepository,
    SqlCategoryRepository,
    SqlOfferRepository,
    SqlPriceHistory,
    SqlProductRepository,
    SqlPurchaseCardRepository,
    SqlStoreRepository,
    SqlSupplierRepository,
)
from zakup.modules.finance.api.router import router as finance_router
from zakup.modules.finance.application.use_cases import (
    ApprovePayment,
    CancelPayment,
    CreatePayment,
    FinanceSettings,
    GetPayment,
    GetProof,
    GetSupplierAccount,
    ListBalances,
    ListPayments,
    PayPayment,
    RegisterObligation,
    RejectPayment,
    SupplierCredit,
    UploadProof,
)
from zakup.modules.finance.domain.finance import PaymentMethod as FinancePaymentMethod
from zakup.modules.finance.infrastructure.adapters import SuppliersAdapter
from zakup.modules.finance.infrastructure.readers import SqlFinanceReader
from zakup.modules.finance.infrastructure.repositories import SqlObligationRepository, SqlPaymentRepository
from zakup.modules.identity.api.router import auth_router, dev_auth_router, me_router, users_router
from zakup.modules.identity.application.use_cases import (
    ActivateUser,
    ChangeMyLocale,
    DeactivateUser,
    GetMyProfile,
    IssueBrowserHandoff,
    ListUsers,
    RefreshSession,
    SetUserRoles,
    SignIn,
    SignInWithTelegram,
    SignOut,
)
from zakup.modules.identity.infrastructure.auth_adapters import (
    JwtAccessTokenIssuer,
    SqlRefreshTokenStore,
    TelegramInitDataVerifier,
)
from zakup.modules.identity.infrastructure.repositories import SqlUserReader, SqlUserRepository
from zakup.modules.integration_iiko.api.router import router as iiko_router
from zakup.modules.integration_iiko.application.exports import (
    EnqueueInvoiceExport,
    ExportNextInvoice,
    ExportScope,
    ExportSettings,
)
from zakup.modules.integration_iiko.application.planning import ImportConsumption, ImportStock
from zakup.modules.integration_iiko.application.runs import ListSyncRuns, RequestSync, ScheduleDailySyncs, SyncScope
from zakup.modules.integration_iiko.application.sync import ImportPurchasePrices, SyncReferences
from zakup.modules.integration_iiko.infrastructure.catalog_adapter import CatalogSyncAdapter
from zakup.modules.integration_iiko.infrastructure.client import HttpIikoGateway, PgAdvisoryLock
from zakup.modules.integration_iiko.infrastructure.exports import BranchAdapter, ReceiptsAdapter, SqlExportQueue
from zakup.modules.integration_iiko.infrastructure.planning_adapter import PlanningAdapter
from zakup.modules.integration_iiko.infrastructure.repositories import SqlLinks, SqlSyncRunReader, SqlSyncRuns
from zakup.modules.notifications.application.use_cases import DeliveriesDigest, NotifyOnEvent, SendNextMessage
from zakup.modules.notifications.infrastructure.sql import SqlDirectory, SqlMessageQueue
from zakup.modules.notifications.infrastructure.telegram import TelegramSender
from zakup.modules.planning.application.facade import DemandQueries, PlanningIngest
from zakup.modules.planning.infrastructure.repositories import SqlPlanningStore
from zakup.modules.procurement.api.router import public_router as procurement_public_router
from zakup.modules.procurement.api.router import router as procurement_router
from zakup.modules.procurement.application.auto import GenerateAutoRequests
from zakup.modules.procurement.application.orders import (
    ApproveOrderChanges,
    CancelOrder,
    GetOrder,
    GetPublicOrder,
    ListOrders,
    OrderSettings,
    RecordOrderResponse,
    SendOrder,
    SupplierRespond,
)
from zakup.modules.procurement.application.receiving_facade import OrderReceiving
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
from zakup.modules.procurement.domain.approval import ApprovalPolicy, SupplierDebtPolicy
from zakup.modules.procurement.domain.order import Tolerance
from zakup.modules.procurement.infrastructure.catalog_adapter import CatalogAdapter
from zakup.modules.procurement.infrastructure.planning_adapter import DemandAdapter
from zakup.modules.procurement.infrastructure.readers import SqlOrderReader, SqlRequestReader
from zakup.modules.procurement.infrastructure.repositories import (
    SqlOrderRepository,
    SqlRequestRepository,
    SqlResponseTokens,
)
from zakup.modules.receiving.api.router import router as receiving_router
from zakup.modules.receiving.application.exports import ReceiptExports
from zakup.modules.receiving.application.use_cases import (
    GetAttachment,
    GetOrderToReceive,
    GetReceipt,
    ListReceipts,
    ResolveDispute,
    SubmitReceipt,
    UploadAttachment,
)
from zakup.modules.receiving.domain.receipt import ReceivingTolerance
from zakup.modules.receiving.infrastructure.adapters import LabelsAdapter, OrdersAdapter
from zakup.modules.receiving.infrastructure.readers import SqlReceiptReader
from zakup.modules.receiving.infrastructure.repositories import (
    LocalAttachments,
    SqlExportStore,
    SqlReceiptRepository,
)
from zakup.platform.access_tokens import AccessTokenCodec, InvalidAccessTokenError
from zakup.platform.di import Stub
from zakup.platform.health import router as health_router
from zakup.platform.outbox import write_events
from zakup.platform.scheduler import DailyJob, DailyScheduler
from zakup.platform.uow import SqlAlchemyUnitOfWork
from zakup.settings import Settings, get_settings
from zakup.shared_kernel.auth import Principal, Role
from zakup.shared_kernel.clock import utc_now

ROUTERS: tuple[APIRouter, ...] = (
    health_router,
    auth_router,
    me_router,
    users_router,
    catalog_router,
    iiko_router,
    procurement_router,
    procurement_public_router,
    receiving_router,
    finance_router,
    analytics_router,
)

T = TypeVar("T")
# Telegram → brauzer o'tish kodi: bir martalik, 2 daqiqa
HANDOFF_TTL_S = 120
Overrides = dict[Callable[..., Any], Callable[..., Any]]


class PerRequest(Protocol):
    def __call__(self, build: Callable[[AsyncSession], T]) -> Callable[[AsyncSession], T]: ...


_bearer = HTTPBearer(auto_error=False, description="POST /auth/telegram javobidagi access_token")


def wire(
    app: FastAPI,
    engine: AsyncEngine,
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> None:
    async def provide_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    def per_request(build: Callable[[AsyncSession], T]) -> Callable[[AsyncSession], T]:
        """Provider: so'rov sessiyasini oladi. Bitta so'rov ichida UoW va repository'lar
        bitta sessiyani ulashadi (FastAPI dependency keshi)."""

        def provider(session: Annotated[AsyncSession, Depends(provide_session)]) -> T:
            return build(session)

        return provider

    overrides = app.dependency_overrides
    overrides[Stub(AsyncEngine)] = lambda: engine
    _wire_identity(app, overrides, per_request, settings)
    _wire_catalog(overrides, per_request)
    _wire_iiko(overrides, per_request, build_iiko_gateway(settings, engine))
    _wire_procurement(overrides, per_request, settings)
    _wire_receiving(overrides, per_request, settings)
    _wire_finance(overrides, per_request, settings)
    overrides[Stub(Reports)] = per_request(
        lambda s: Reports(SqlAnalyticsReader(s), window_days=settings.demand_window_days)
    )


def _wire_identity(
    app: FastAPI,
    overrides: Overrides,
    per_request: PerRequest,
    settings: Settings,
) -> None:
    codec = AccessTokenCodec(settings.jwt_secret.get_secret_value(), settings.access_token_ttl_s)
    access = JwtAccessTokenIssuer(codec)
    verifier = TelegramInitDataVerifier(
        settings.telegram_bot_token.get_secret_value(), settings.telegram_init_data_ttl_s
    )
    bootstrap_admin_ids = frozenset(settings.bootstrap_admin_ids)

    def provide_principal(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    ) -> Principal:
        if credentials is None:
            raise InvalidAccessTokenError("auth.token_missing")
        return codec.decode(credentials.credentials)

    def refresh_store(session: AsyncSession) -> SqlRefreshTokenStore:
        return SqlRefreshTokenStore(session, settings.refresh_token_ttl_s)

    provide_sign_in = per_request(
        lambda session: SignIn(
            SqlAlchemyUnitOfWork(session),
            SqlUserRepository(session),
            access=access,
            refresh=refresh_store(session),
            bootstrap_admin_ids=bootstrap_admin_ids,
        )
    )

    def provide_sign_in_with_telegram(sign_in: Annotated[SignIn, Depends(provide_sign_in)]) -> SignInWithTelegram:
        return SignInWithTelegram(verifier, sign_in)

    overrides[Stub(Principal)] = provide_principal
    overrides[Stub(SignIn)] = provide_sign_in
    overrides[Stub(SignInWithTelegram)] = provide_sign_in_with_telegram
    overrides[Stub(RefreshSession)] = per_request(
        lambda session: RefreshSession(
            SqlAlchemyUnitOfWork(session), SqlUserRepository(session), access, refresh_store(session)
        )
    )
    overrides[Stub(IssueBrowserHandoff)] = per_request(
        lambda session: IssueBrowserHandoff(
            SqlAlchemyUnitOfWork(session), SqlUserRepository(session), SqlRefreshTokenStore(session, HANDOFF_TTL_S)
        )
    )
    overrides[Stub(SignOut)] = per_request(
        lambda session: SignOut(SqlAlchemyUnitOfWork(session), refresh_store(session))
    )
    overrides[Stub(GetMyProfile)] = per_request(lambda session: GetMyProfile(SqlUserReader(session)))
    overrides[Stub(ChangeMyLocale)] = per_request(
        lambda session: ChangeMyLocale(SqlAlchemyUnitOfWork(session), SqlUserRepository(session))
    )
    overrides[Stub(ListUsers)] = per_request(lambda session: ListUsers(SqlUserReader(session)))
    overrides[Stub(ActivateUser)] = per_request(
        lambda session: ActivateUser(SqlAlchemyUnitOfWork(session), SqlUserRepository(session))
    )
    overrides[Stub(DeactivateUser)] = per_request(
        lambda session: DeactivateUser(
            SqlAlchemyUnitOfWork(session), SqlUserRepository(session), refresh_store(session)
        )
    )
    overrides[Stub(SetUserRoles)] = per_request(
        lambda session: SetUserRoles(SqlAlchemyUnitOfWork(session), SqlUserRepository(session))
    )

    if settings.dev_auth_bypass:
        app.include_router(dev_auth_router, prefix="/api/v1")


def _wire_catalog(overrides: Overrides, per_request: PerRequest) -> None:
    def uow(session: AsyncSession) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session)

    providers: dict[type, Callable[[AsyncSession], Any]] = {
        ListSuppliers: lambda s: ListSuppliers(SqlSupplierReader(s)),
        GetSupplier: lambda s: GetSupplier(SqlSupplierReader(s)),
        RegisterSupplier: lambda s: RegisterSupplier(uow(s), SqlSupplierRepository(s)),
        ReviseSupplier: lambda s: ReviseSupplier(uow(s), SqlSupplierRepository(s)),
        ArchiveSupplier: lambda s: ArchiveSupplier(uow(s), SqlSupplierRepository(s)),
        ListStores: lambda s: ListStores(SqlStoreReader(s)),
        RegisterStore: lambda s: RegisterStore(uow(s), SqlStoreRepository(s)),
        ReviseStore: lambda s: ReviseStore(uow(s), SqlStoreRepository(s)),
        ArchiveStore: lambda s: ArchiveStore(uow(s), SqlStoreRepository(s)),
        ListCategories: lambda s: ListCategories(SqlCategoryReader(s)),
        CreateCategory: lambda s: CreateCategory(uow(s), SqlCategoryRepository(s)),
        ListProducts: lambda s: ListProducts(SqlProductReader(s)),
        GetProduct: lambda s: GetProduct(SqlProductReader(s)),
        RegisterProduct: lambda s: RegisterProduct(uow(s), SqlProductRepository(s), SqlCategoryRepository(s)),
        ReviseProduct: lambda s: ReviseProduct(uow(s), SqlProductRepository(s), SqlCategoryRepository(s)),
        ArchiveProduct: lambda s: ArchiveProduct(uow(s), SqlProductRepository(s)),
        AddOffer: lambda s: AddOffer(
            uow(s), SqlOfferRepository(s), SqlPriceHistory(s), SqlSupplierRepository(s), SqlProductRepository(s)
        ),
        ReviseOffer: lambda s: ReviseOffer(uow(s), SqlOfferRepository(s), SqlPriceHistory(s)),
        ArchiveOffer: lambda s: ArchiveOffer(uow(s), SqlOfferRepository(s)),
        GetPriceHistory: lambda s: GetPriceHistory(SqlPriceHistoryReader(s)),
        ConfigurePurchaseCard: lambda s: ConfigurePurchaseCard(
            uow(s),
            SqlPurchaseCardRepository(s),
            SqlProductRepository(s),
            SqlStoreRepository(s),
            SqlSupplierRepository(s),
        ),
    }
    for use_case, build in providers.items():
        overrides[Stub(use_case)] = per_request(build)


# ---------------------------------------------------------------- iiko (API va worker uchun umumiy)


def build_iiko_gateway(settings: Settings, engine: AsyncEngine) -> HttpIikoGateway:
    return HttpIikoGateway(
        settings.iiko_servers, PgAdvisoryLock(engine, settings.iiko_lock_wait_s), timeout_s=settings.iiko_timeout_s
    )


def planning_sync(session: AsyncSession) -> PlanningAdapter:
    return PlanningAdapter(PlanningIngest(SqlPlanningStore(session)))


def iiko_scope_factory(session_factory: async_sessionmaker[AsyncSession]) -> Callable[[], Any]:
    """Worker: har qadam — alohida sessiya/tranzaksiya (runs + links + catalog bitta sessiyada)."""

    @asynccontextmanager
    async def scope() -> AsyncIterator[SyncScope]:
        async with session_factory() as session:
            links = SqlLinks(session)
            catalog = CatalogSyncAdapter(
                IikoCatalogSync(
                    branches=SqlBranchRepository(session),
                    stores=SqlStoreRepository(session),
                    categories=SqlCategoryRepository(session),
                    products=SqlProductRepository(session),
                    suppliers=SqlSupplierRepository(session),
                    offers=SqlOfferRepository(session),
                    history=SqlPriceHistory(session),
                )
            )
            yield SyncScope(
                runs=SqlSyncRuns(session),
                references=SyncReferences(links, catalog),
                prices=ImportPurchasePrices(links, catalog),
                stock=ImportStock(links, planning_sync(session)),
                consumption=ImportConsumption(links, planning_sync(session)),
                commit=session.commit,
            )

    return scope


def _wire_iiko(overrides: Overrides, per_request: PerRequest, gateway: HttpIikoGateway) -> None:
    overrides[Stub(RequestSync)] = per_request(lambda s: RequestSync(gateway, SqlSyncRuns(s), s.commit))
    overrides[Stub(ListSyncRuns)] = per_request(lambda s: ListSyncRuns(gateway, SqlSyncRunReader(s)))


# ---------------------------------------------------------------- procurement


def catalog_queries(session: AsyncSession) -> CatalogQueries:
    """catalog public interfeysi — boshqa modullar adapterlari shu orqali (bitta sessiyada)."""
    return CatalogQueries(
        offers=SqlOfferRepository(session),
        products=SqlProductRepository(session),
        suppliers=SqlSupplierRepository(session),
        stores=SqlStoreRepository(session),
        branches=SqlBranchRepository(session),
        cards=SqlPurchaseCardRepository(session),
        offers_by_product=SqlOffersByProduct(session),
        labels=SqlLabelReader(session),
    )


def catalog_port(session: AsyncSession) -> CatalogAdapter:
    return CatalogAdapter(catalog_queries(session))


def _wire_procurement(overrides: Overrides, per_request: PerRequest, settings: Settings) -> None:
    policy = ApprovalPolicy({Role(role): limit for role, limit in settings.approval_limits.items()})
    order_settings = OrderSettings(
        tolerance=Tolerance(price_pct=settings.price_tolerance_pct, abs_max=settings.price_tolerance_abs),
        response_hours=settings.supplier_response_hours,
        public_base_url=settings.public_base_url,
        company_name=settings.company_name,
    )

    def uow(session: AsyncSession) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session)

    requests, orders = SqlRequestRepository, SqlOrderRepository
    providers: dict[type, Callable[[AsyncSession], Any]] = {
        CreateRequest: lambda s: CreateRequest(uow(s), requests(s), catalog_port(s)),
        ReviseRequest: lambda s: ReviseRequest(uow(s), requests(s)),
        AddRequestLine: lambda s: AddRequestLine(uow(s), requests(s), catalog_port(s)),
        ChangeRequestLine: lambda s: ChangeRequestLine(uow(s), requests(s)),
        RemoveRequestLine: lambda s: RemoveRequestLine(uow(s), requests(s)),
        ChooseLineOffer: lambda s: ChooseLineOffer(uow(s), requests(s), catalog_port(s)),
        SubmitRequest: lambda s: SubmitRequest(uow(s), requests(s)),
        ApproveRequest: lambda s: ApproveRequest(
            uow(s),
            requests(s),
            orders(s),
            catalog_port(s),
            policy=policy,
            credit=SupplierCredit(SqlFinanceReader(s), SuppliersAdapter(catalog_queries(s))),
            debt_policy=SupplierDebtPolicy(settings.supplier_debt_policy),
        ),
        ReturnRequest: lambda s: ReturnRequest(uow(s), requests(s)),
        RejectRequest: lambda s: RejectRequest(uow(s), requests(s)),
        CancelRequest: lambda s: CancelRequest(uow(s), requests(s)),
        ListRequests: lambda s: ListRequests(SqlRequestReader(s), catalog_port(s)),
        GetRequest: lambda s: GetRequest(SqlRequestReader(s), SqlOrderReader(s), catalog_port(s)),
        ListOrders: lambda s: ListOrders(SqlOrderReader(s), catalog_port(s)),
        GetOrder: lambda s: GetOrder(SqlOrderReader(s), catalog_port(s)),
        SendOrder: lambda s: SendOrder(
            uow(s), orders(s), SqlOrderReader(s), SqlResponseTokens(s), catalog_port(s), settings=order_settings
        ),
        RecordOrderResponse: lambda s: RecordOrderResponse(uow(s), orders(s), order_settings),
        ApproveOrderChanges: lambda s: ApproveOrderChanges(uow(s), orders(s), policy),
        CancelOrder: lambda s: CancelOrder(uow(s), orders(s)),
        GetPublicOrder: lambda s: GetPublicOrder(SqlResponseTokens(s), SqlOrderReader(s), catalog_port(s)),
        SupplierRespond: lambda s: SupplierRespond(uow(s), orders(s), SqlResponseTokens(s), order_settings),
        GenerateAutoRequests: lambda s: auto_requests(s, settings),
    }
    for use_case, build in providers.items():
        overrides[Stub(use_case)] = per_request(build)


def auto_requests(session: AsyncSession, settings: Settings) -> GenerateAutoRequests:
    return GenerateAutoRequests(
        SqlAlchemyUnitOfWork(session),
        SqlRequestRepository(session),
        SqlOrderRepository(session),
        catalog_port(session),
        demand=DemandAdapter(DemandQueries(SqlPlanningStore(session), window_days=settings.demand_window_days)),
    )


# ---------------------------------------------------------------- receiving


def orders_for_receiving(session: AsyncSession) -> OrdersAdapter:
    return OrdersAdapter(OrderReceiving(SqlOrderRepository(session), catalog_port(session)))


def _wire_receiving(overrides: Overrides, per_request: PerRequest, settings: Settings) -> None:
    tolerance = ReceivingTolerance(
        qty_weight_pct=settings.receiving_qty_weight_pct,
        qty_piece_pct=settings.receiving_qty_piece_pct,
        price_pct=settings.receiving_price_pct,
    )
    media = Path(settings.media_dir)

    def uow(session: AsyncSession) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session)

    providers: dict[type, Callable[[AsyncSession], Any]] = {
        GetOrderToReceive: lambda s: GetOrderToReceive(orders_for_receiving(s)),
        SubmitReceipt: lambda s: SubmitReceipt(
            uow(s), SqlReceiptRepository(s), orders_for_receiving(s), LocalAttachments(s, media), tolerance=tolerance
        ),
        ResolveDispute: lambda s: ResolveDispute(uow(s), SqlReceiptRepository(s)),
        UploadAttachment: lambda s: UploadAttachment(uow(s), LocalAttachments(s, media)),
        GetAttachment: lambda s: GetAttachment(LocalAttachments(s, media)),
        ListReceipts: lambda s: ListReceipts(SqlReceiptReader(s), LabelsAdapter(catalog_queries(s))),
        GetReceipt: lambda s: GetReceipt(SqlReceiptReader(s), LabelsAdapter(catalog_queries(s))),
    }
    for use_case, build in providers.items():
        overrides[Stub(use_case)] = per_request(build)


# ---------------------------------------------------------------- finance


def _wire_finance(overrides: Overrides, per_request: PerRequest, settings: Settings) -> None:
    media = Path(settings.media_dir)
    finance_settings = FinanceSettings(payment_approval_required=settings.payment_approval_required)

    def uow(session: AsyncSession) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session)

    def suppliers(session: AsyncSession) -> SuppliersAdapter:
        return SuppliersAdapter(catalog_queries(session))

    payments, obligations, reader = SqlPaymentRepository, SqlObligationRepository, SqlFinanceReader
    providers: dict[type, Callable[[AsyncSession], Any]] = {
        ListBalances: lambda s: ListBalances(reader(s), payments(s), suppliers(s)),
        GetSupplierAccount: lambda s: GetSupplierAccount(reader(s), payments(s), suppliers(s)),
        CreatePayment: lambda s: CreatePayment(uow(s), payments(s), obligations(s), finance_settings),
        ApprovePayment: lambda s: ApprovePayment(uow(s), payments(s), obligations(s)),
        RejectPayment: lambda s: RejectPayment(uow(s), payments(s), obligations(s)),
        CancelPayment: lambda s: CancelPayment(uow(s), payments(s), obligations(s)),
        # To'lov tasdig'i — umumiy fayl omborida (receiving.attachments)
        PayPayment: lambda s: PayPayment(uow(s), payments(s), obligations(s), LocalAttachments(s, media)),
        ListPayments: lambda s: ListPayments(reader(s), suppliers(s)),
        GetPayment: lambda s: GetPayment(reader(s), suppliers(s)),
        UploadProof: lambda s: UploadProof(uow(s), LocalAttachments(s, media)),
        GetProof: lambda s: GetProof(LocalAttachments(s, media)),
    }
    for use_case, build in providers.items():
        overrides[Stub(use_case)] = per_request(build)


# ---------------------------------------------------------------- worker: outbox va iiko kirimi


def _receipts_port(session: AsyncSession) -> ReceiptsAdapter:
    return ReceiptsAdapter(ReceiptExports(SqlExportStore(session)))


def outbox_handlers(settings: Settings | None = None) -> dict[str, Callable[[AsyncSession, dict[str, Any]], Any]]:
    """Event → modul reaksiyasi (ARCHITECTURE §3.1.2): receiving ular haqida hech narsa bilmaydi.

    Bot xabarlari (notifications) — har eventga qo'shimcha reaksiya: navbatga yoziladi, worker yuboradi.
    """
    settings = settings or get_settings()

    async def register_obligation(session: AsyncSession, payload: dict[str, Any], *, blocked: bool) -> None:
        register = RegisterObligation(
            SqlObligationRepository(session), SuppliersAdapter(catalog_queries(session)), SqlPaymentRepository(session)
        )
        # Qabulda joyida to'langan bo'lsa — majburiyat darhol to'lov bilan yopiladi (eski event'larda maydon yo'q)
        method = payload.get("payment_method") if payload.get("paid_on_delivery") else None
        payments = await register(
            receipt_id=UUID(payload["aggregate_id"]),
            receipt_number=payload["number"],
            supplier_id=UUID(payload["supplier_id"]),
            store_id=UUID(payload["store_id"]),
            amount=Decimal(payload["amount"]),
            received_at=datetime.fromisoformat(payload["received_at"]),
            blocked=blocked,
            paid_on_delivery=FinancePaymentMethod(method) if method else None,
            received_by=UUID(payload["received_by"]) if payload.get("received_by") else None,
        )
        for payment in payments:
            await write_events(session, payment.aggregate_type, payment.pull_events())

    async def receipt_accepted(session: AsyncSession, payload: dict[str, Any]) -> None:
        # Ikkala reaksiya ham idempotent: xato bo'lsa event to'liq qayta ishlanadi
        await EnqueueInvoiceExport(SqlExportQueue(session), _receipts_port(session))(UUID(payload["aggregate_id"]))
        await register_obligation(session, payload, blocked=False)

    async def receipt_disputed(session: AsyncSession, payload: dict[str, Any]) -> None:
        await register_obligation(session, payload, blocked=True)

    handlers: dict[str, Callable[[AsyncSession, dict[str, Any]], Any]] = {
        "receiving.receipt_accepted": receipt_accepted,
        "receiving.receipt_disputed": receipt_disputed,
    }
    if not settings.notifications_enabled:
        return handlers

    def notifier(session: AsyncSession) -> NotifyOnEvent:
        return NotifyOnEvent(SqlDirectory(session), SqlMessageQueue(session), settings.approval_limits)

    def with_notification(event_type: str, first: Callable[[AsyncSession, dict[str, Any]], Any] | None) -> Any:
        async def handle(session: AsyncSession, payload: dict[str, Any]) -> None:
            if first is not None:
                await first(session, payload)
            # Bot xatosi asosiy reaksiyani (majburiyat, iiko navbati) qaytarmasin: alohida savepoint,
            # xato — logga; xabar yo'qoladi, hisob-kitob emas
            try:
                async with session.begin_nested():
                    await notifier(session)(event_type, payload)
            except Exception:
                structlog.get_logger().exception("notification_enqueue_failed", event_type=event_type)

        return handle

    for event_type in NotifyOnEvent.RULES:
        handlers[event_type] = with_notification(event_type, handlers.get(event_type))
    return handlers


def build_notification_sender(
    settings: Settings, session_factory: async_sessionmaker[AsyncSession]
) -> Callable[[], Any]:
    """Worker: navbatdan bitta xabar → Telegram. Token yo'q yoki o'chiq bo'lsa — hech narsa qilmaydi."""
    token = settings.telegram_bot_token.get_secret_value()
    if not settings.notifications_enabled or not token:

        async def idle() -> bool:
            return False

        return idle
    sender = TelegramSender(token)

    async def send_next() -> bool:
        async with session_factory() as session:
            return await SendNextMessage(SqlMessageQueue(session), sender, settings.public_base_url, session.commit)()

    return send_next


def build_invoice_exporter(
    settings: Settings, gateway: HttpIikoGateway, session_factory: async_sessionmaker[AsyncSession]
) -> ExportNextInvoice:
    @asynccontextmanager
    async def scope() -> AsyncIterator[ExportScope]:
        async with session_factory() as session:
            yield ExportScope(
                queue=SqlExportQueue(session),
                receipts=_receipts_port(session),
                branches=BranchAdapter(catalog_queries(session)),
                links=SqlLinks(session),
                commit=session.commit,
            )

    return ExportNextInvoice(
        gateway,
        scope,
        ExportSettings(post_processed=settings.iiko_post_invoices, disputed_processed=settings.iiko_post_disputed),
    )


def build_daily_scheduler(
    settings: Settings, gateway: HttpIikoGateway, session_factory: async_sessionmaker[AsyncSession]
) -> DailyScheduler:
    """Ertalab: iiko sinxroni (narx, sarf, qoldiq) → bir soatdan keyin avto-zayavka qoralamalari."""

    async def daily_syncs() -> None:
        async with session_factory() as session:
            backfill = not await DemandQueries(SqlPlanningStore(session)).has_history()
            await ScheduleDailySyncs(gateway, SqlSyncRuns(session), session.commit)(backfill=backfill)

    async def auto() -> None:
        async with session_factory() as session:
            await auto_requests(session, settings)(None)

    async def deliveries_digest() -> None:
        async with session_factory() as session:
            await DeliveriesDigest(SqlDirectory(session), SqlMessageQueue(session), utc_now)()
            await session.commit()

    digest_hour = settings.deliveries_digest_hour if settings.notifications_enabled else None
    return DailyScheduler(
        session_factory,
        [
            DailyJob("iiko_daily_sync", settings.daily_sync_hour, daily_syncs),
            DailyJob("auto_requests", settings.auto_requests_hour, auto),
            DailyJob("deliveries_digest", digest_hour, deliveries_digest),
        ],
    )
