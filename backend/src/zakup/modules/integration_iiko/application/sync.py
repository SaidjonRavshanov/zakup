"""iiko → bizning ma'lumotnoma. Sinxronizatsiya inkremental, kalit — iiko GUID (WORKFLOW B1).

Qoidalar:
- iiko'dan faqat o'qiymiz; tovar iiko'da yaratilmaydi (WORKFLOW 16-bo'shliq).
- Xaridga faqat GOODS turidagi, o'chirilmagan tovarlar olinadi.
- Bir xil tovar boshqa serverda boshqa GUID bilan bo'lishi mumkin → avval link, keyin artikul (iiko "num") bo'yicha.
- Yetkazuvchining "НАЛ"/"ПЕР" kartochkalari — bitta yetkazuvchi, ikki to'lov usuli.
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID

from zakup.modules.integration_iiko.application.ports import CatalogSync, EntityKind, IikoReader, Links
from zakup.modules.integration_iiko.domain.mapping import (
    is_purchasable,
    parse_supplier_name,
    payment_method_from_comment,
    unit_code,
)
from zakup.modules.integration_iiko.domain.models import (
    DepartmentType,
    IikoIncomingInvoice,
    IikoProduct,
    IikoProductGroup,
    IikoSupplier,
)


@dataclass
class Stats:
    counts: Counter[str] = field(default_factory=Counter)

    def add(self, key: str, n: int = 1) -> None:
        self.counts[key] += n

    def as_dict(self) -> dict[str, int]:
        return dict(sorted(self.counts.items()))


class SyncReferences:
    def __init__(self, links: Links, catalog: CatalogSync) -> None:
        self._links = links
        self._catalog = catalog

    async def __call__(self, server: str, reader: IikoReader) -> dict[str, int]:
        stats = Stats()
        branches = await self._branches(server, reader, stats)
        await self._stores(server, reader, branches, stats)
        units = {unit.id: code for unit in await reader.units() if (code := unit_code(unit))}
        products = [p for p in await reader.products() if is_purchasable(p)]
        categories = await self._categories(server, await reader.product_groups(), products, stats)
        await self._products(server, products, units, categories, stats)
        await self._suppliers(server, await reader.suppliers(), stats)
        return stats.as_dict()

    async def _branches(self, server: str, reader: IikoReader, stats: Stats) -> dict[UUID, UUID]:
        result = {}
        for dept in await reader.departments():
            if dept.type is not DepartmentType.DEPARTMENT:
                continue
            local = await self._linked(server, EntityKind.BRANCH, dept.id)
            branch_id = await self._catalog.upsert_branch(local, iiko_id=dept.id, code=dept.code, name=dept.name)
            await self._links.save(server, EntityKind.BRANCH, dept.id, branch_id)
            result[dept.id] = branch_id
            stats.add("branches")
        return result

    async def _stores(self, server: str, reader: IikoReader, branches: dict[UUID, UUID], stats: Stats) -> None:
        for store in await reader.stores():
            local = await self._linked(server, EntityKind.STORE, store.id)
            branch_id = branches.get(store.department_id) if store.department_id else None
            store_id = await self._catalog.upsert_store(local, iiko_id=store.id, name=store.name, branch_id=branch_id)
            await self._links.save(server, EntityKind.STORE, store.id, store_id)
            stats.add("stores")

    async def _categories(
        self, server: str, groups: list[IikoProductGroup], products: list[IikoProduct], stats: Stats
    ) -> dict[UUID, UUID]:
        """Faqat xarid qilinadigan tovarlar joylashgan guruhlar va ularning ota-guruhlari (ota — avval)."""
        by_id = {g.id: g for g in groups if not g.deleted}
        needed: list[IikoProductGroup] = []
        for group_id in {p.group_id for p in products if p.group_id}:
            for group in _ancestry(by_id, group_id):
                if group not in needed:
                    needed.append(group)
        result: dict[UUID, UUID] = {}
        for group in sorted(needed, key=lambda g: len(_ancestry(by_id, g.id))):
            local = await self._linked(server, EntityKind.CATEGORY, group.id)
            parent = result.get(group.parent_id) if group.parent_id else None
            category_id = await self._catalog.upsert_category(
                local, iiko_id=group.id, name=group.name, parent_id=parent
            )
            await self._links.save(server, EntityKind.CATEGORY, group.id, category_id)
            result[group.id] = category_id
            stats.add("categories")
        return result

    async def _products(
        self,
        server: str,
        products: Iterable[IikoProduct],
        units: dict[UUID, str],
        categories: dict[UUID, UUID],
        stats: Stats,
    ) -> None:
        for product in products:
            base_unit = units.get(product.unit_id) if product.unit_id else None
            if base_unit is None:
                stats.add("products_skipped_unit")
                continue
            local = await self._linked(server, EntityKind.PRODUCT, product.id)
            if local is None and product.article:
                local = await self._catalog.find_product_by_article(product.article)
            product_id = await self._catalog.upsert_product(
                local,
                iiko_id=product.id,
                name=product.name,
                article=product.article,
                base_unit=base_unit,
                category_id=categories.get(product.group_id) if product.group_id else None,
                archived=product.deleted,
            )
            await self._links.save(server, EntityKind.PRODUCT, product.id, product_id, key=product.article)
            stats.add("products" if local else "products_new")

    async def _suppliers(self, server: str, suppliers: list[IikoSupplier], stats: Stats) -> None:
        for supplier in suppliers:
            if supplier.represents_store or supplier.deleted:
                stats.add("suppliers_skipped")
                continue
            name = parse_supplier_name(supplier.name)
            local = await self._linked(server, EntityKind.SUPPLIER, supplier.id) or await self._links.local_id_by_key(
                EntityKind.SUPPLIER, name.key
            )
            supplier_id = await self._catalog.upsert_supplier(
                local,
                iiko_id=supplier.id,
                name=name.display,
                phone=supplier.phone,
                inn=supplier.inn,
                payment_method=name.payment_method,
            )
            attrs = {
                "payment_method": name.payment_method.value if name.payment_method else None,
                "name": supplier.name,
            }
            await self._links.save(server, EntityKind.SUPPLIER, supplier.id, supplier_id, key=name.key, attrs=attrs)
            stats.add("suppliers" if local else "suppliers_new")

    async def _linked(self, server: str, kind: EntityKind, iiko_id: UUID) -> UUID | None:
        return await self._links.local_id(server, kind, iiko_id) or await self._links.local_id_any_server(kind, iiko_id)


def _ancestry(groups: dict[UUID, IikoProductGroup], group_id: UUID) -> list[IikoProductGroup]:
    """[ildiz, ..., guruhning o'zi]; sikl bo'lsa to'xtaydi."""
    chain: list[IikoProductGroup] = []
    current = groups.get(group_id)
    while current is not None and current not in chain:
        chain.insert(0, current)
        current = groups.get(current.parent_id) if current.parent_id else None
    return chain


class ImportPurchasePrices:
    """O'tkazilgan kirim nakladnoylaridan (yetkazuvchi, tovar) bo'yicha oxirgi narx → taklif + narx tarixi.

    Tarnov'da iiko prays-listlari bo'sh: xarid narxi faqat nakladnoyda — shuning uchun narx ustasi bizning tizim.
    """

    def __init__(self, links: Links, catalog: CatalogSync) -> None:
        self._links = links
        self._catalog = catalog

    async def __call__(self, server: str, reader: IikoReader, date_from: date, date_to: date) -> dict[str, int]:
        stats = Stats()
        invoices = await reader.incoming_invoices(date_from, date_to)
        latest: dict[tuple[UUID, UUID], tuple[date, Decimal]] = {}
        for invoice in sorted(invoices, key=lambda i: i.incoming_date):
            await self._collect(server, invoice, latest, stats)
        for (supplier_id, product_id), (on, price) in latest.items():
            changed = await self._catalog.record_purchase_price(
                supplier_id=supplier_id, product_id=product_id, price_per_base_unit=price, on=on
            )
            stats.add("prices_recorded" if changed else "prices_unchanged")
        return stats.as_dict()

    async def _collect(
        self,
        server: str,
        invoice: IikoIncomingInvoice,
        latest: dict[tuple[UUID, UUID], tuple[date, Decimal]],
        stats: Stats,
    ) -> None:
        stats.add("invoices")
        if not invoice.is_processed or invoice.supplier_id is None:
            stats.add("invoices_skipped")
            return
        supplier_id = await self._links.local_id(server, EntityKind.SUPPLIER, invoice.supplier_id)
        if supplier_id is None:  # ombor-kontragent (ko'chirish) yoki hali sinxronlanmagan
            stats.add("invoices_unknown_supplier")
            return
        if payment_method_from_comment(invoice.comment):
            stats.add("invoices_with_payment_mark")
        for item in invoice.items:
            product_id = await self._links.local_id(server, EntityKind.PRODUCT, item.product_id)
            if product_id is None or item.price <= 0:
                stats.add("items_skipped")
                continue
            latest[(supplier_id, product_id)] = (invoice.incoming_date, item.price)
            stats.add("items")
