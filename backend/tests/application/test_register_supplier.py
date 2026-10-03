"""Use case testi: DB'siz, fake port'lar bilan (DIP'ning amaliy foydasi)."""

from uuid import UUID

import pytest

from tests.application.fakes import FakeUoW
from zakup.modules.catalog.application.dto import RegisterSupplierCommand
from zakup.modules.catalog.application.use_cases import RegisterSupplier
from zakup.modules.catalog.domain.supplier import DuplicateInnError, PaymentTerms, Supplier
from zakup.shared_kernel.auth import Principal, Role, RoleGrant
from zakup.shared_kernel.errors import PermissionDeniedError
from zakup.shared_kernel.ids import new_id

BUYER = Principal(user_id=new_id(), grants=frozenset({RoleGrant(Role.BUYER)}))


class InMemorySuppliers:
    def __init__(self) -> None:
        self.items: dict[UUID, Supplier] = {}

    async def get(self, supplier_id: UUID) -> Supplier | None:
        return self.items.get(supplier_id)

    async def exists_by_inn(self, inn: str) -> bool:
        return any(s.inn == inn and not s.is_archived for s in self.items.values())

    async def add(self, supplier: Supplier) -> None:
        self.items[supplier.id] = supplier

    async def save(self, supplier: Supplier) -> None:
        self.items[supplier.id] = supplier


async def test_registers_and_publishes_event() -> None:
    uow, repo = FakeUoW(), InMemorySuppliers()
    supplier_id = await RegisterSupplier(uow, repo)(
        RegisterSupplierCommand(
            name="Meat Pro", inn="305000111", payment_terms=PaymentTerms.DEFERRED, deferral_days=14
        ),
        BUYER,
    )
    assert supplier_id in repo.items
    assert uow.committed
    assert [e.event_type for e in uow.published] == ["catalog.supplier_registered"]


async def test_duplicate_inn_is_rejected_without_commit() -> None:
    uow, repo = FakeUoW(), InMemorySuppliers()
    use_case = RegisterSupplier(uow, repo)
    cmd = RegisterSupplierCommand(name="A", inn="305000111", payment_terms=PaymentTerms.PREPAY)
    await use_case(cmd, BUYER)
    uow.committed = False

    with pytest.raises(DuplicateInnError):
        await use_case(cmd, BUYER)
    assert not uow.committed


async def test_only_buyer_or_admin_can_register() -> None:
    uow, repo = FakeUoW(), InMemorySuppliers()
    initiator = Principal(user_id=new_id(), grants=frozenset({RoleGrant(Role.INITIATOR)}))
    with pytest.raises(PermissionDeniedError):
        await RegisterSupplier(uow, repo)(
            RegisterSupplierCommand(name="A", inn=None, payment_terms=PaymentTerms.PREPAY), initiator
        )
    assert not repo.items
