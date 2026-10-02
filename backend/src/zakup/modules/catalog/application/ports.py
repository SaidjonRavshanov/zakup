"""Catalog moduli port'lari — implementatsiyalar infrastructure qatlamida (DIP, ISP)."""

from typing import Protocol
from uuid import UUID

from zakup.modules.catalog.application.dto import SupplierListItem
from zakup.modules.catalog.domain.supplier import Supplier


class SupplierRepository(Protocol):
    """Yozish tomoni: aggregate'ni to'liq yuklaydi/saqlaydi."""

    async def get(self, supplier_id: UUID) -> Supplier | None: ...

    async def exists_by_inn(self, inn: str) -> bool: ...

    async def add(self, supplier: Supplier) -> None: ...

    async def save(self, supplier: Supplier) -> None:
        """Optimistic lock: version mos kelmasa ConflictError."""


class SupplierReader(Protocol):
    """O'qish tomoni (CQRS-lite): to'g'ridan-to'g'ri DTO, aggregate yaratilmaydi."""

    async def list(self, *, include_archived: bool, search: str | None, limit: int) -> list[SupplierListItem]: ...
