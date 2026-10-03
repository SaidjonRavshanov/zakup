"""Ombor (iiko'dagi склад): kuxnya, bar, asosiy ombor. Asosan iiko'dan sinxronlanadi (WORKFLOW B1)."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Self
from uuid import UUID

from zakup.shared_kernel.errors import DomainError
from zakup.shared_kernel.events import AggregateRoot, DomainEvent
from zakup.shared_kernel.ids import new_id

MAX_NAME = 200


class InvalidStoreError(DomainError):
    code = "invalid_store"


@dataclass(frozen=True, kw_only=True)
class StoreRegistered(DomainEvent):
    event_type: ClassVar[str] = "catalog.store_registered"
    name: str


@dataclass(frozen=True, kw_only=True)
class StoreArchived(DomainEvent):
    event_type: ClassVar[str] = "catalog.store_archived"


class Store(AggregateRoot):
    aggregate_type: ClassVar[str] = "catalog.store"

    def __init__(
        self,
        *,
        id: UUID,  # noqa: A002 — domen atamasi
        name: str,
        address: str | None,
        branch_id: UUID | None = None,
        iiko_id: UUID | None = None,
        archived_at: datetime | None = None,
        version: int = 1,
    ) -> None:
        super().__init__()
        self.id = id
        self.name = name
        self.address = address
        self.branch_id = branch_id
        self.iiko_id = iiko_id
        self.archived_at = archived_at
        self.version = version

    @classmethod
    def register(
        cls, *, name: str, address: str | None = None, branch_id: UUID | None = None, iiko_id: UUID | None = None
    ) -> Self:
        store = cls(id=new_id(), name=_clean_name(name), address=_clean(address), branch_id=branch_id, iiko_id=iiko_id)
        store.record(StoreRegistered(aggregate_id=store.id, name=store.name))
        return store

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    def revise(self, *, name: str, address: str | None) -> None:
        self.name = _clean_name(name)
        self.address = _clean(address)

    def assign_branch(self, branch_id: UUID | None) -> None:
        self.branch_id = branch_id

    def archive(self, at: datetime) -> None:
        if self.is_archived:
            return
        self.archived_at = at
        self.record(StoreArchived(aggregate_id=self.id))


def _clean(value: str | None) -> str | None:
    value = " ".join(value.split()) if value else None
    return value or None


def _clean_name(name: str) -> str:
    cleaned = _clean(name)
    if not cleaned:
        raise InvalidStoreError("store.name_empty")
    if len(cleaned) > MAX_NAME:
        raise InvalidStoreError("store.name_too_long", max=MAX_NAME)
    return cleaned
