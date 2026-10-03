"""Omborlar: asosan iiko'dan keladi; qo'lda — iiko ulanmaguncha (admin)."""

from uuid import UUID

from zakup.modules.catalog.application.common import load
from zakup.modules.catalog.application.dto import StoreItem
from zakup.modules.catalog.application.ports import StoreReader, StoreRepository
from zakup.modules.catalog.domain.store import Store
from zakup.shared_kernel.auth import Principal, Role
from zakup.shared_kernel.clock import Clock, utc_now
from zakup.shared_kernel.uow import UnitOfWork


class RegisterStore:
    def __init__(self, uow: UnitOfWork, stores: StoreRepository) -> None:
        self._uow = uow
        self._stores = stores

    async def __call__(self, actor: Principal, *, name: str, address: str | None) -> UUID:
        actor.require(Role.ADMIN)
        async with self._uow:
            store = Store.register(name=name, address=address)
            await self._stores.add(store)
            self._uow.track(store)
            await self._uow.commit()
            return store.id


class ReviseStore:
    def __init__(self, uow: UnitOfWork, stores: StoreRepository) -> None:
        self._uow = uow
        self._stores = stores

    async def __call__(self, actor: Principal, store_id: UUID, *, name: str, address: str | None) -> None:
        actor.require(Role.ADMIN)
        async with self._uow:
            store = await load(self._stores, store_id, "store.not_found")
            store.revise(name=name, address=address)
            await self._stores.save(store)
            await self._uow.commit()


class ArchiveStore:
    def __init__(self, uow: UnitOfWork, stores: StoreRepository, clock: Clock = utc_now) -> None:
        self._uow = uow
        self._stores = stores
        self._clock = clock

    async def __call__(self, actor: Principal, store_id: UUID) -> None:
        actor.require(Role.ADMIN)
        async with self._uow:
            store = await load(self._stores, store_id, "store.not_found")
            store.archive(self._clock())
            await self._stores.save(store)
            self._uow.track(store)
            await self._uow.commit()


class ListStores:
    def __init__(self, reader: StoreReader) -> None:
        self._reader = reader

    async def __call__(self, *, include_archived: bool = False) -> list[StoreItem]:
        return await self._reader.list(include_archived=include_archived)
