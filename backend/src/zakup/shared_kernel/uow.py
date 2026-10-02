"""Unit of Work port'i — application qatlami faqat shu interfeysni biladi (DIP)."""

from types import TracebackType
from typing import Protocol, Self

from zakup.shared_kernel.events import AggregateRoot


class UnitOfWork(Protocol):
    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def track(self, aggregate: AggregateRoot) -> None:
        """Commit paytida aggregate event'lari outbox'ga yoziladi."""

    async def commit(self) -> None: ...
