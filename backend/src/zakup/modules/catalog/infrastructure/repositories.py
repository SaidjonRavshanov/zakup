from typing import Any
from uuid import UUID

from sqlalchemy import exists, func, insert, select, update
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from zakup.modules.catalog.application.dto import SupplierListItem
from zakup.modules.catalog.domain.supplier import PaymentTerms, Supplier
from zakup.modules.catalog.infrastructure.tables import suppliers
from zakup.shared_kernel.errors import ConflictError
from zakup.shared_kernel.money import Money


def _to_row(supplier: Supplier) -> dict[str, Any]:
    return {
        "id": supplier.id,
        "iiko_id": supplier.iiko_id,
        "name": supplier.name,
        "inn": supplier.inn,
        "payment_terms": supplier.payment_terms.value,
        "deferral_days": supplier.deferral_days,
        "credit_limit": supplier.credit_limit.amount,
        "min_order_amount": supplier.min_order_amount.amount,
        "currency": supplier.credit_limit.currency,
        "archived_at": supplier.archived_at,
    }


def _to_domain(row: RowMapping) -> Supplier:
    return Supplier(
        id=row["id"],
        iiko_id=row["iiko_id"],
        name=row["name"],
        inn=row["inn"],
        payment_terms=PaymentTerms(row["payment_terms"]),
        deferral_days=row["deferral_days"],
        credit_limit=Money(row["credit_limit"], row["currency"]),
        min_order_amount=Money(row["min_order_amount"], row["currency"]),
        archived_at=row["archived_at"],
        version=row["version"],
    )


class SqlSupplierRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, supplier_id: UUID) -> Supplier | None:
        row = (await self._session.execute(select(suppliers).where(suppliers.c.id == supplier_id))).mappings().first()
        return _to_domain(row) if row else None

    async def exists_by_inn(self, inn: str) -> bool:
        query = select(exists().where(suppliers.c.inn == inn, suppliers.c.archived_at.is_(None)))
        return bool(await self._session.scalar(query))

    async def add(self, supplier: Supplier) -> None:
        await self._session.execute(insert(suppliers).values(**_to_row(supplier), version=supplier.version))

    async def save(self, supplier: Supplier) -> None:
        result = await self._session.execute(
            update(suppliers)
            .where(suppliers.c.id == supplier.id, suppliers.c.version == supplier.version)
            .values(**_to_row(supplier), version=supplier.version + 1, updated_at=func.now())
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise ConflictError("supplier.modified")
        supplier.version += 1


class SqlSupplierReader:
    """O'qish: faqat kerakli ustunlar → DTO (ORM hydratsiyasiz)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, *, include_archived: bool, search: str | None, limit: int) -> list[SupplierListItem]:
        query = select(
            suppliers.c.id,
            suppliers.c.name,
            suppliers.c.inn,
            suppliers.c.payment_terms,
            suppliers.c.deferral_days,
            suppliers.c.credit_limit,
            suppliers.c.archived_at,
        ).order_by(suppliers.c.name, suppliers.c.id)
        if not include_archived:
            query = query.where(suppliers.c.archived_at.is_(None))
        if search:
            query = query.where(suppliers.c.name.icontains(search, autoescape=True) | (suppliers.c.inn == search))
        rows = (await self._session.execute(query.limit(limit))).all()
        return [
            SupplierListItem(
                id=row.id,
                name=row.name,
                inn=row.inn,
                payment_terms=PaymentTerms(row.payment_terms),
                deferral_days=row.deferral_days,
                credit_limit=row.credit_limit,
                archived=row.archived_at is not None,
            )
            for row in rows
        ]
