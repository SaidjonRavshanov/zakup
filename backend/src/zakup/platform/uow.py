from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from zakup.platform.outbox import write_events
from zakup.shared_kernel.events import AggregateRoot


class SqlAlchemyUnitOfWork:
    """`shared_kernel.uow.UnitOfWork` implementatsiyasi.

    Commit: aggregate event'lari → platform.outbox → COMMIT (hammasi bitta tranzaksiyada).
    Commit chaqirilmasa yoki xato bo'lsa — rollback.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._tracked: list[AggregateRoot] = []

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self.session.in_transaction():
            await self.session.rollback()
        self._tracked.clear()

    def track(self, aggregate: AggregateRoot) -> None:
        self._tracked.append(aggregate)

    async def commit(self) -> None:
        for aggregate in self._tracked:
            await write_events(self.session, aggregate.aggregate_type, aggregate.pull_events())
        await self.session.commit()
