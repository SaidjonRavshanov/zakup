"""Application testlari uchun umumiy fake port'lar."""

from types import TracebackType
from typing import Self

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
