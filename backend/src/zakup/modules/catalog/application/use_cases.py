"""Use case'lar: har biri — bitta vazifa, bitta public metod (SRP)."""

from uuid import UUID

from zakup.modules.catalog.application.dto import RegisterSupplierCommand, SupplierListItem
from zakup.modules.catalog.application.ports import SupplierReader, SupplierRepository
from zakup.modules.catalog.domain.supplier import DuplicateInnError, Supplier
from zakup.shared_kernel.auth import Principal, Role
from zakup.shared_kernel.money import Money
from zakup.shared_kernel.uow import UnitOfWork

MAX_PAGE_SIZE = 200


class RegisterSupplier:
    def __init__(self, uow: UnitOfWork, suppliers: SupplierRepository) -> None:
        self._uow = uow
        self._suppliers = suppliers

    async def __call__(self, cmd: RegisterSupplierCommand, actor: Principal) -> UUID:
        actor.require(Role.BUYER, Role.ADMIN)
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
            )
            await self._suppliers.add(supplier)
            self._uow.track(supplier)
            await self._uow.commit()
            return supplier.id


class ListSuppliers:
    def __init__(self, reader: SupplierReader) -> None:
        self._reader = reader

    async def __call__(
        self, *, include_archived: bool = False, search: str | None = None, limit: int = 50
    ) -> list[SupplierListItem]:
        return await self._reader.list(
            include_archived=include_archived,
            search=search.strip() if search else None,
            limit=max(1, min(limit, MAX_PAGE_SIZE)),
        )
