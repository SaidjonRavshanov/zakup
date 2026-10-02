"""Use case testi: DB'siz, fake port'lar bilan (DIP'ning amaliy foydasi)."""

from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from zakup.modules.catalog.application.dto import RegisterSupplierCommand
from zakup.modules.catalog.application.use_cases import RegisterSupplier
from zakup.modules.catalog.domain.supplier import DuplicateInnError, PaymentTerms, Supplier
from zakup.shared_kernel.events import AggregateRoot, DomainEvent


class FakeUoW:
    def __init__(self) -> None:
        self.committed = False
        self.published: list[DomainEvent] = []
        self._tracked: list[AggregateRoot] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self, et: type[BaseException] | None, e: BaseException | None, tb: TracebackType | None
    ) -> None:
        self._tracked.clear()

    def track(self, aggregate: AggregateRoot) -> None:
        self._tracked.append(aggregate)

    async def commit(self) -> None:
        for aggregate in self._tracked:
            self.published.extend(aggregate.pull_events())
        self.committed = True


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
        RegisterSupplierCommand(name="Meat Pro", inn="305000111", payment_terms=PaymentTerms.DEFERRED, deferral_days=14)
    )
    assert supplier_id in repo.items
    assert uow.committed
    assert [e.event_type for e in uow.published] == ["catalog.supplier_registered"]


async def test_duplicate_inn_is_rejected_without_commit() -> None:
    uow, repo = FakeUoW(), InMemorySuppliers()
    use_case = RegisterSupplier(uow, repo)
    cmd = RegisterSupplierCommand(name="A", inn="305000111", payment_terms=PaymentTerms.PREPAY)
    await use_case(cmd)
    uow.committed = False

    with pytest.raises(DuplicateInnError):
        await use_case(cmd)
    assert not uow.committed
