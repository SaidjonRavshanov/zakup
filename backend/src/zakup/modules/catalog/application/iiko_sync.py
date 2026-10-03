"""catalog modulining iiko sinxronizatsiyasi uchun public interfeysi (ARCHITECTURE §3.1).

integration_iiko bu yerga faqat primitivlar bilan murojaat qiladi va catalog jadvallarini bilmaydi.
Tizim amali — foydalanuvchi ruxsati tekshirilmaydi; tranzaksiya chaqiruvchida (worker).

Ustunlik qoidalari:
- iiko — tovar, ombor, filial, kategoriya ustasi: nom/artikul/birlik har sinxronda yangilanadi;
- yetkazuvchi — bizda tahrirlanadi (shartlar, jadval): sinxron faqat yangisini yaratadi, bo'sh kontaktni
  to'ldiradi va to'lov usulini qo'shadi;
- narx — bizning tizim (iiko prays-listlari bo'sh): nakladnoydagi narx narx tarixiga `iiko` manbasi bilan yoziladi.
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from zakup.modules.catalog.application.ports import (
    BranchRepository,
    CategoryRepository,
    OfferRepository,
    PriceHistory,
    ProductRepository,
    StoreRepository,
    SupplierRepository,
)
from zakup.modules.catalog.domain.branch import Branch
from zakup.modules.catalog.domain.offer import Packaging, PriceSource, SupplierOffer
from zakup.modules.catalog.domain.product import Product, ProductCategory, Unit
from zakup.modules.catalog.domain.store import Store
from zakup.modules.catalog.domain.supplier import (
    Contacts,
    PaymentMethod,
    PaymentTerms,
    Supplier,
    normalize_inn,
    normalize_phone,
)
from zakup.shared_kernel.clock import Clock, utc_now


class IikoCatalogSync:
    def __init__(
        self,
        *,
        branches: BranchRepository,
        stores: StoreRepository,
        categories: CategoryRepository,
        products: ProductRepository,
        suppliers: SupplierRepository,
        offers: OfferRepository,
        history: PriceHistory,
        clock: Clock = utc_now,
    ) -> None:
        self._branches = branches
        self._stores = stores
        self._categories = categories
        self._products = products
        self._suppliers = suppliers
        self._offers = offers
        self._history = history
        self._clock = clock

    async def upsert_branch(self, local_id: UUID | None, *, iiko_id: UUID, code: str | None, name: str) -> UUID:
        branch = await self._branches.get(local_id) if local_id else None
        if branch is None:
            branch = Branch.register(name=name, code=code, iiko_id=iiko_id)
            await self._branches.add(branch)
        elif (branch.name, branch.code) != (" ".join(name.split()), code):
            branch.revise(name=name, code=code)
            await self._branches.save(branch)
        return branch.id

    async def upsert_store(self, local_id: UUID | None, *, iiko_id: UUID, name: str, branch_id: UUID | None) -> UUID:
        store = await self._stores.get(local_id) if local_id else None
        if store is None:
            store = Store.register(name=name, branch_id=branch_id, iiko_id=iiko_id)
            await self._stores.add(store)
        elif (store.name, store.branch_id) != (" ".join(name.split()), branch_id):
            store.revise(name=name, address=store.address)
            store.assign_branch(branch_id)
            await self._stores.save(store)
        return store.id

    async def upsert_category(self, local_id: UUID | None, *, iiko_id: UUID, name: str, parent_id: UUID | None) -> UUID:
        category = await self._categories.get(local_id) if local_id else None
        if category is None:
            category = ProductCategory.create(name=name, parent_id=parent_id)
            category.iiko_id = iiko_id
            await self._categories.add(category)
        elif (category.name, category.parent_id) != (" ".join(name.split()), parent_id):
            category.name = " ".join(name.split()) or category.name
            category.parent_id = parent_id
            await self._categories.save(category)
        return category.id

    async def find_product_by_article(self, article: str) -> UUID | None:
        product = await self._products.find_by_article(article)
        return product.id if product else None

    async def upsert_product(
        self,
        local_id: UUID | None,
        *,
        iiko_id: UUID,
        name: str,
        article: str | None,
        base_unit: str,
        category_id: UUID | None,
        archived: bool,
    ) -> UUID:
        product = await self._products.get(local_id) if local_id else None
        if product is None:
            product = Product.register(
                name=name, base_unit=Unit(base_unit), article=article, category_id=category_id, iiko_id=iiko_id
            )
            await self._products.add(product)
        else:
            before = (product.name, product.article, product.base_unit, product.category_id, product.is_archived)
            product.revise(name=name, article=article, base_unit=Unit(base_unit), category_id=category_id)
            if archived:
                product.archive(self._clock())
            if before != (product.name, product.article, product.base_unit, product.category_id, product.is_archived):
                await self._products.save(product)
        return product.id

    async def upsert_supplier(
        self,
        local_id: UUID | None,
        *,
        iiko_id: UUID,
        name: str,
        phone: str | None,
        inn: str | None,
        payment_method: str | None,
    ) -> UUID:
        method = PaymentMethod(payment_method) if payment_method else None
        supplier = await self._suppliers.get(local_id) if local_id else None
        if supplier is None:
            valid_inn = normalize_inn(inn)
            if valid_inn and await self._suppliers.exists_by_inn(valid_inn):
                valid_inn = None
            supplier = Supplier.register(
                name=name,
                inn=valid_inn,
                payment_terms=PaymentTerms.ON_DELIVERY,  # haqiqiy shart — xaridor tomonidan to'ldiriladi
                contacts=Contacts(phone=normalize_phone(phone)),
                payment_methods=frozenset({method}) if method else frozenset(),
                iiko_id=iiko_id,
            )
            await self._suppliers.add(supplier)
            return supplier.id

        before = (supplier.payment_methods, supplier.contacts)
        if method:
            supplier.accept_payment_method(method)
        supplier.fill_missing_contacts(phone=normalize_phone(phone))
        if before != (supplier.payment_methods, supplier.contacts):
            await self._suppliers.save(supplier)
        return supplier.id

    async def record_purchase_price(
        self, *, supplier_id: UUID, product_id: UUID, price_per_base_unit: Decimal, on: date
    ) -> bool:
        """Nakladnoydan: (yetkazuvchi, tovar) uchun 1 bazaviy birlik taklifi; eskiroq sana — e'tiborsiz."""
        offer = await self._offers.find(supplier_id=supplier_id, product_id=product_id, supplier_sku=None)
        if offer is None:
            product = await self._products.get(product_id)
            if product is None:
                return False
            offer, record = SupplierOffer.create(
                supplier_id=supplier_id,
                product_id=product_id,
                packaging=Packaging(product.base_unit, Decimal(1)),
                price=price_per_base_unit,
                valid_from=on,
                source=PriceSource.IIKO,
            )
            await self._offers.add(offer)
            await self._history.append(record)
            return True
        if on < offer.price_valid_from:
            return False
        changed = offer.change_price(price_per_base_unit, on, PriceSource.IIKO)
        if changed is None:
            return False
        await self._offers.save(offer)
        await self._history.append(changed)
        return True
