"""Yetkazib beruvchi use case'lari: har biri — bitta vazifa, bitta public metod (SRP)."""

from uuid import UUID

from zakup.modules.catalog.application.common import load, page_size
from zakup.modules.catalog.application.dto import (
    ContactsData,
    RegisterSupplierCommand,
    SupplierDetail,
    SupplierListItem,
)
from zakup.modules.catalog.application.ports import SupplierReader, SupplierRepository
from zakup.modules.catalog.domain.supplier import Contacts, DuplicateInnError, OrderSchedule, Supplier
from zakup.shared_kernel.auth import Principal, Role
from zakup.shared_kernel.clock import Clock, utc_now
from zakup.shared_kernel.errors import NotFoundError
from zakup.shared_kernel.money import Money
from zakup.shared_kernel.uow import UnitOfWork

EDITORS = (Role.BUYER, Role.ADMIN)


def _schedule(cmd: RegisterSupplierCommand) -> OrderSchedule:
    return OrderSchedule(
        lead_time_days=cmd.lead_time_days,
        order_weekdays=frozenset(cmd.order_weekdays),
        delivery_weekdays=frozenset(cmd.delivery_weekdays),
        order_cutoff=cmd.order_cutoff,
    )


def _contacts(data: ContactsData) -> Contacts:
    def clean(value: str | None) -> str | None:
        return (value or "").strip() or None

    return Contacts(
        phone=clean(data.phone), telegram=clean(data.telegram), email=clean(data.email), person=clean(data.person)
    )


class RegisterSupplier:
    def __init__(self, uow: UnitOfWork, suppliers: SupplierRepository) -> None:
        self._uow = uow
        self._suppliers = suppliers

    async def __call__(self, cmd: RegisterSupplierCommand, actor: Principal) -> UUID:
        actor.require(*EDITORS)
        async with self._uow:
            if cmd.inn and await self._suppliers.exists_by_inn(cmd.inn.strip()):
                raise DuplicateInnError("supplier.duplicate_inn", inn=cmd.inn)
            supplier = Supplier.register(
                name=cmd.name,
                inn=cmd.inn,
                payment_terms=cmd.payment_terms,
                deferral_days=cmd.deferral_days,
                credit_limit=Money(cmd.credit_limit),
                min_order_amount=Money(cmd.min_order_amount),
                schedule=_schedule(cmd),
                contacts=_contacts(cmd.contacts),
            )
            await self._suppliers.add(supplier)
            self._uow.track(supplier)
            await self._uow.commit()
            return supplier.id


class ReviseSupplier:
    def __init__(self, uow: UnitOfWork, suppliers: SupplierRepository) -> None:
        self._uow = uow
        self._suppliers = suppliers

    async def __call__(self, supplier_id: UUID, cmd: RegisterSupplierCommand, actor: Principal) -> None:
        actor.require(*EDITORS)
        async with self._uow:
            supplier = await load(self._suppliers, supplier_id, "supplier.not_found")
            inn = cmd.inn.strip() if cmd.inn else None
            if inn and await self._suppliers.exists_by_inn(inn, exclude_id=supplier.id):
                raise DuplicateInnError("supplier.duplicate_inn", inn=inn)
            supplier.revise(
                name=cmd.name,
                inn=inn,
                payment_terms=cmd.payment_terms,
                deferral_days=cmd.deferral_days,
                credit_limit=Money(cmd.credit_limit),
                min_order_amount=Money(cmd.min_order_amount),
                schedule=_schedule(cmd),
                contacts=_contacts(cmd.contacts),
            )
            await self._suppliers.save(supplier)
            self._uow.track(supplier)
            await self._uow.commit()


class ArchiveSupplier:
    def __init__(self, uow: UnitOfWork, suppliers: SupplierRepository, clock: Clock = utc_now) -> None:
        self._uow = uow
        self._suppliers = suppliers
        self._clock = clock

    async def __call__(self, supplier_id: UUID, actor: Principal) -> None:
        actor.require(*EDITORS)
        async with self._uow:
            supplier = await load(self._suppliers, supplier_id, "supplier.not_found")
            supplier.archive(self._clock())
            await self._suppliers.save(supplier)
            self._uow.track(supplier)
            await self._uow.commit()


class ListSuppliers:
    def __init__(self, reader: SupplierReader) -> None:
        self._reader = reader

    async def __call__(
        self, *, include_archived: bool = False, search: str | None = None, limit: int = 50
    ) -> list[SupplierListItem]:
        return await self._reader.list(
            include_archived=include_archived,
            search=search.strip() if search else None,
            limit=page_size(limit),
        )


class GetSupplier:
    def __init__(self, reader: SupplierReader) -> None:
        self._reader = reader

    async def __call__(self, supplier_id: UUID) -> SupplierDetail:
        detail = await self._reader.detail(supplier_id)
        if detail is None:
            raise NotFoundError("supplier.not_found")
        return detail
