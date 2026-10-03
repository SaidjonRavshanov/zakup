"""Composition root: barcha implementatsiyalar port'larga **faqat shu yerda** ulanadi (ARCHITECTURE §4).

Yangi modul qo'shish: router'ni `ROUTERS` ga, provider'larni `_wire_*` ga qo'shing.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Any, Protocol, TypeVar

from fastapi import APIRouter, Depends, FastAPI
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

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
from zakup.modules.identity.api.router import auth_router, dev_auth_router, me_router, users_router
from zakup.modules.identity.application.use_cases import (
    ActivateUser,
    ChangeMyLocale,
    DeactivateUser,
    GetMyProfile,
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
from zakup.modules.integration_iiko.application.runs import ListSyncRuns, RequestSync, SyncScope
from zakup.modules.integration_iiko.application.sync import ImportPurchasePrices, SyncReferences
from zakup.modules.integration_iiko.infrastructure.catalog_adapter import CatalogSyncAdapter
from zakup.modules.integration_iiko.infrastructure.client import HttpIikoGateway, PgAdvisoryLock
from zakup.modules.integration_iiko.infrastructure.repositories import SqlLinks, SqlSyncRunReader, SqlSyncRuns
from zakup.platform.access_tokens import AccessTokenCodec, InvalidAccessTokenError
from zakup.platform.di import Stub
from zakup.platform.health import router as health_router
from zakup.platform.uow import SqlAlchemyUnitOfWork
from zakup.settings import Settings
from zakup.shared_kernel.auth import Principal

ROUTERS: tuple[APIRouter, ...] = (health_router, auth_router, me_router, users_router, catalog_router, iiko_router)

T = TypeVar("T")
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
                commit=session.commit,
            )

    return scope


def _wire_iiko(overrides: Overrides, per_request: PerRequest, gateway: HttpIikoGateway) -> None:
    overrides[Stub(RequestSync)] = per_request(lambda s: RequestSync(gateway, SqlSyncRuns(s), s.commit))
    overrides[Stub(ListSyncRuns)] = per_request(lambda s: ListSyncRuns(gateway, SqlSyncRunReader(s)))
