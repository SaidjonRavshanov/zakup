"""Filial (iiko'dagi bo'lim — department): Sebzar, Drujba, Keles, Chorsu, Istirohat.

Har filialda o'z omborlari; Tarnov'da har filialning o'z iikoRMS serveri bor (Istirohat'dan tashqari).
"""

from datetime import datetime
from typing import ClassVar, Self
from uuid import UUID

from zakup.shared_kernel.errors import DomainError
from zakup.shared_kernel.events import AggregateRoot
from zakup.shared_kernel.ids import new_id


class InvalidBranchError(DomainError):
    code = "invalid_branch"


class Branch(AggregateRoot):
    aggregate_type: ClassVar[str] = "catalog.branch"

    def __init__(
        self,
        *,
        id: UUID,  # noqa: A002 — domen atamasi
        name: str,
        code: str | None,
        iiko_id: UUID | None = None,
        archived_at: datetime | None = None,
        version: int = 1,
    ) -> None:
        super().__init__()
        self.id = id
        self.name = name
        self.code = code
        self.iiko_id = iiko_id
        self.archived_at = archived_at
        self.version = version

    @classmethod
    def register(cls, *, name: str, code: str | None = None, iiko_id: UUID | None = None) -> Self:
        return cls(id=new_id(), name=_clean_name(name), code=(code or "").strip() or None, iiko_id=iiko_id)

    def revise(self, *, name: str, code: str | None) -> None:
        self.name = _clean_name(name)
        self.code = (code or "").strip() or None


def _clean_name(name: str) -> str:
    cleaned = " ".join(name.split())
    if not cleaned:
        raise InvalidBranchError("branch.name_empty")
    return cleaned
