"""finance port'lari → catalog public interfeysi (CatalogQueries)."""

from collections.abc import Iterable
from uuid import UUID

from zakup.modules.catalog.application.queries import CatalogQueries
from zakup.modules.finance.application.ports import PaymentTerms


class SuppliersAdapter:
    def __init__(self, catalog: CatalogQueries) -> None:
        self._catalog = catalog

    async def terms(self, supplier_id: UUID) -> PaymentTerms | None:
        terms = await self._catalog.supplier_terms(supplier_id)
        if terms is None:
            return None
        return PaymentTerms(name=terms.name, deferral_days=terms.deferral_days, credit_limit=terms.credit_limit)

    async def labels(
        self, *, suppliers: Iterable[UUID] = (), stores: Iterable[UUID] = ()
    ) -> tuple[dict[UUID, str], dict[UUID, str]]:
        labels = await self._catalog.labels(suppliers=suppliers, stores=stores)
        return labels.suppliers, labels.stores
