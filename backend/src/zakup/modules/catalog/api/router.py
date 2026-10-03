"""HTTP ↔ use case moslashtirish. Biznes mantiq va ruxsat tekshiruvi yo'q — ular use case'da (ARCHITECTURE §4)."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from zakup.modules.catalog.api.schemas import (
    CategoryIn,
    CategoryOut,
    CreatedOut,
    NewOfferIn,
    PriceHistoryOut,
    ProductDetailOut,
    ProductIn,
    ProductOut,
    PurchaseCardIn,
    RegisterSupplierIn,
    ReviseOfferIn,
    StoreIn,
    StoreOut,
    SupplierDetailOut,
    SupplierOut,
)
from zakup.modules.catalog.application.offers import AddOffer, ArchiveOffer, GetPriceHistory, ReviseOffer
from zakup.modules.catalog.application.products import (
    ArchiveProduct,
    CreateCategory,
    GetProduct,
    ListCategories,
    ListProducts,
    RegisterProduct,
    ReviseProduct,
)
from zakup.modules.catalog.application.purchase_cards import ConfigurePurchaseCard
from zakup.modules.catalog.application.stores import ArchiveStore, ListStores, RegisterStore, ReviseStore
from zakup.modules.catalog.application.use_cases import (
    ArchiveSupplier,
    GetSupplier,
    ListSuppliers,
    RegisterSupplier,
    ReviseSupplier,
)
from zakup.platform.di import Stub
from zakup.platform.security import CurrentPrincipal

router = APIRouter(prefix="/catalog", tags=["catalog"])

NO_CONTENT = status.HTTP_204_NO_CONTENT
Search = Annotated[str | None, Query(max_length=100)]
Limit = Annotated[int, Query(ge=1, le=200)]


def use(cls: type) -> Any:
    """`Depends(Stub(cls))` qisqartmasi — implementatsiya bootstrap.py da ulanadi."""
    return Depends(Stub(cls))


# ---------------------------------------------------------------- yetkazib beruvchilar


@router.get("/suppliers")
async def list_suppliers(
    _: CurrentPrincipal,
    use_case: Annotated[ListSuppliers, use(ListSuppliers)],
    search: Search = None,
    include_archived: bool = False,
    limit: Limit = 50,
) -> list[SupplierOut]:
    items = await use_case(include_archived=include_archived, search=search, limit=limit)
    return [SupplierOut.model_validate(item) for item in items]


@router.post("/suppliers", status_code=status.HTTP_201_CREATED)
async def register_supplier(
    body: RegisterSupplierIn, actor: CurrentPrincipal, use_case: Annotated[RegisterSupplier, use(RegisterSupplier)]
) -> CreatedOut:
    return CreatedOut(id=await use_case(body.to_command(), actor))


@router.get("/suppliers/{supplier_id}")
async def get_supplier(
    supplier_id: UUID, _: CurrentPrincipal, use_case: Annotated[GetSupplier, use(GetSupplier)]
) -> SupplierDetailOut:
    return SupplierDetailOut.model_validate(await use_case(supplier_id))


@router.put("/suppliers/{supplier_id}", status_code=NO_CONTENT)
async def revise_supplier(
    supplier_id: UUID,
    body: RegisterSupplierIn,
    actor: CurrentPrincipal,
    use_case: Annotated[ReviseSupplier, use(ReviseSupplier)],
) -> None:
    await use_case(supplier_id, body.to_command(), actor)


@router.post("/suppliers/{supplier_id}/archive", status_code=NO_CONTENT)
async def archive_supplier(
    supplier_id: UUID, actor: CurrentPrincipal, use_case: Annotated[ArchiveSupplier, use(ArchiveSupplier)]
) -> None:
    await use_case(supplier_id, actor)


# ---------------------------------------------------------------- takliflar va narxlar


@router.post("/suppliers/{supplier_id}/offers", status_code=status.HTTP_201_CREATED)
async def add_offer(
    supplier_id: UUID, body: NewOfferIn, actor: CurrentPrincipal, use_case: Annotated[AddOffer, use(AddOffer)]
) -> CreatedOut:
    return CreatedOut(id=await use_case(actor, supplier_id, body.product_id, body.to_command(), body.price))


@router.put("/offers/{offer_id}", status_code=NO_CONTENT)
async def revise_offer(
    offer_id: UUID, body: ReviseOfferIn, actor: CurrentPrincipal, use_case: Annotated[ReviseOffer, use(ReviseOffer)]
) -> None:
    await use_case(actor, offer_id, body.to_command(), body.price, body.price_valid_from)


@router.post("/offers/{offer_id}/archive", status_code=NO_CONTENT)
async def archive_offer(
    offer_id: UUID, actor: CurrentPrincipal, use_case: Annotated[ArchiveOffer, use(ArchiveOffer)]
) -> None:
    await use_case(actor, offer_id)


@router.get("/offers/{offer_id}/price-history")
async def price_history(
    offer_id: UUID, _: CurrentPrincipal, use_case: Annotated[GetPriceHistory, use(GetPriceHistory)]
) -> list[PriceHistoryOut]:
    return [PriceHistoryOut.model_validate(item) for item in await use_case(offer_id)]


# ---------------------------------------------------------------- omborlar


@router.get("/stores")
async def list_stores(
    _: CurrentPrincipal, use_case: Annotated[ListStores, use(ListStores)], include_archived: bool = False
) -> list[StoreOut]:
    return [StoreOut.model_validate(item) for item in await use_case(include_archived=include_archived)]


@router.post("/stores", status_code=status.HTTP_201_CREATED)
async def register_store(
    body: StoreIn, actor: CurrentPrincipal, use_case: Annotated[RegisterStore, use(RegisterStore)]
) -> CreatedOut:
    return CreatedOut(id=await use_case(actor, name=body.name, address=body.address))


@router.put("/stores/{store_id}", status_code=NO_CONTENT)
async def revise_store(
    store_id: UUID, body: StoreIn, actor: CurrentPrincipal, use_case: Annotated[ReviseStore, use(ReviseStore)]
) -> None:
    await use_case(actor, store_id, name=body.name, address=body.address)


@router.post("/stores/{store_id}/archive", status_code=NO_CONTENT)
async def archive_store(
    store_id: UUID, actor: CurrentPrincipal, use_case: Annotated[ArchiveStore, use(ArchiveStore)]
) -> None:
    await use_case(actor, store_id)


# ---------------------------------------------------------------- kategoriyalar va tovarlar


@router.get("/categories")
async def list_categories(
    _: CurrentPrincipal, use_case: Annotated[ListCategories, use(ListCategories)]
) -> list[CategoryOut]:
    return [CategoryOut.model_validate(item) for item in await use_case()]


@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryIn, actor: CurrentPrincipal, use_case: Annotated[CreateCategory, use(CreateCategory)]
) -> CreatedOut:
    return CreatedOut(
        id=await use_case(actor, name=body.name, parent_id=body.parent_id, monthly_budget=body.monthly_budget)
    )


@router.get("/products")
async def list_products(
    _: CurrentPrincipal,
    use_case: Annotated[ListProducts, use(ListProducts)],
    search: Search = None,
    category_id: UUID | None = None,
    include_archived: bool = False,
    limit: Limit = 50,
) -> list[ProductOut]:
    items = await use_case(include_archived=include_archived, search=search, category_id=category_id, limit=limit)
    return [ProductOut.model_validate(item) for item in items]


@router.post("/products", status_code=status.HTTP_201_CREATED)
async def register_product(
    body: ProductIn, actor: CurrentPrincipal, use_case: Annotated[RegisterProduct, use(RegisterProduct)]
) -> CreatedOut:
    return CreatedOut(id=await use_case(actor, body.to_command()))


@router.get("/products/{product_id}")
async def get_product(
    product_id: UUID, _: CurrentPrincipal, use_case: Annotated[GetProduct, use(GetProduct)]
) -> ProductDetailOut:
    return ProductDetailOut.model_validate(await use_case(product_id))


@router.put("/products/{product_id}", status_code=NO_CONTENT)
async def revise_product(
    product_id: UUID, body: ProductIn, actor: CurrentPrincipal, use_case: Annotated[ReviseProduct, use(ReviseProduct)]
) -> None:
    await use_case(actor, product_id, body.to_command())


@router.post("/products/{product_id}/archive", status_code=NO_CONTENT)
async def archive_product(
    product_id: UUID, actor: CurrentPrincipal, use_case: Annotated[ArchiveProduct, use(ArchiveProduct)]
) -> None:
    await use_case(actor, product_id)


# ---------------------------------------------------------------- xarid kartochkasi


@router.put("/purchase-cards")
async def configure_purchase_card(
    body: PurchaseCardIn,
    actor: CurrentPrincipal,
    use_case: Annotated[ConfigurePurchaseCard, use(ConfigurePurchaseCard)],
) -> CreatedOut:
    return CreatedOut(id=await use_case(actor, body.to_command()))
