"""HTTP ↔ use case moslashtirish. Biznes mantiq yo'q (ARCHITECTURE §4)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from zakup.modules.catalog.api.schemas import CreatedOut, RegisterSupplierIn, SupplierOut
from zakup.modules.catalog.application.dto import RegisterSupplierCommand
from zakup.modules.catalog.application.use_cases import ListSuppliers, RegisterSupplier
from zakup.platform.di import Stub

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/suppliers")
async def list_suppliers(
    use_case: Annotated[ListSuppliers, Depends(Stub(ListSuppliers))],
    search: Annotated[str | None, Query(max_length=100)] = None,
    include_archived: bool = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[SupplierOut]:
    items = await use_case(include_archived=include_archived, search=search, limit=limit)
    return [SupplierOut.model_validate(item) for item in items]


@router.post("/suppliers", status_code=status.HTTP_201_CREATED)
async def register_supplier(
    body: RegisterSupplierIn,
    use_case: Annotated[RegisterSupplier, Depends(Stub(RegisterSupplier))],
) -> CreatedOut:
    supplier_id = await use_case(RegisterSupplierCommand(**body.model_dump()))
    return CreatedOut(id=supplier_id)
