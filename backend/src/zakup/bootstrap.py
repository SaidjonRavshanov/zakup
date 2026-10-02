"""Composition root: barcha implementatsiyalar port'larga **faqat shu yerda** ulanadi (ARCHITECTURE §4).

Yangi modul qo'shish: router'ni `ROUTERS` ga, provider'larni `_wire_*` ga qo'shing.
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from zakup.modules.catalog.api.router import router as catalog_router
from zakup.modules.catalog.application.use_cases import ListSuppliers, RegisterSupplier
from zakup.modules.catalog.infrastructure.repositories import SqlSupplierReader, SqlSupplierRepository
from zakup.platform.di import Stub
from zakup.platform.health import router as health_router
from zakup.platform.uow import SqlAlchemyUnitOfWork

ROUTERS: tuple[APIRouter, ...] = (health_router, catalog_router)


def wire(app: FastAPI, engine: AsyncEngine, session_factory: async_sessionmaker[AsyncSession]) -> None:
    async def provide_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    Session = Annotated[AsyncSession, Depends(provide_session)]  # noqa: N806

    # Bitta so'rov ichida UoW va repository bitta sessiyani ulashadi (FastAPI dependency keshi)
    def provide_list_suppliers(session: Session) -> ListSuppliers:
        return ListSuppliers(SqlSupplierReader(session))

    def provide_register_supplier(session: Session) -> RegisterSupplier:
        return RegisterSupplier(SqlAlchemyUnitOfWork(session), SqlSupplierRepository(session))

    overrides = app.dependency_overrides
    overrides[Stub(AsyncEngine)] = lambda: engine
    overrides[Stub(ListSuppliers)] = provide_list_suppliers
    overrides[Stub(RegisterSupplier)] = provide_register_supplier
