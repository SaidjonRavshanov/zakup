"""Domain event'lar va aggregate bazasi.

Aggregate o'zgarganda event yig'adi; Unit of Work commit paytida ularni
platform.outbox ga **shu tranzaksiyada** yozadi (ADR-04).
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import ClassVar
from uuid import UUID

from zakup.shared_kernel.ids import uuid7


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    event_type: ClassVar[str]
    aggregate_id: UUID
    event_id: UUID = field(default_factory=uuid7)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AggregateRoot:
    aggregate_type: ClassVar[str]

    def __init__(self) -> None:
        self._events: list[DomainEvent] = []

    def record(self, event: DomainEvent) -> None:
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        events, self._events = self._events, []
        return events
