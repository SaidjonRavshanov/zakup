"""iiko sinxronizatsiyasi: holat va qo'lda ishga tushirish. API iiko'ga o'zi chiqmaydi — navbatga qo'yadi (ADR-05)."""

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field

from zakup.modules.integration_iiko.application.ports import SyncKind, SyncStatus
from zakup.modules.integration_iiko.application.runs import ListSyncRuns, RequestSync
from zakup.platform.di import Stub
from zakup.platform.security import CurrentPrincipal

router = APIRouter(prefix="/iiko", tags=["iiko"])


class ServerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    department_code: str | None


class SyncRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    server_code: str
    kind: SyncKind
    status: SyncStatus
    params: dict[str, Any]
    stats: dict[str, int]
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class SyncOverviewOut(BaseModel):
    servers: list[ServerOut]
    runs: list[SyncRunOut]


class SyncRequestIn(BaseModel):
    server_code: str = Field(min_length=1, max_length=32)
    kind: SyncKind
    days: int | None = Field(default=None, ge=1, le=120)


class CreatedOut(BaseModel):
    id: UUID


@router.get("/sync")
async def sync_overview(
    actor: CurrentPrincipal,
    use_case: Annotated[ListSyncRuns, Depends(Stub(ListSyncRuns))],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SyncOverviewOut:
    servers, runs = await use_case(actor, limit=limit)
    return SyncOverviewOut(
        servers=[ServerOut.model_validate(s) for s in servers], runs=[SyncRunOut.model_validate(r) for r in runs]
    )


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def request_sync(
    body: SyncRequestIn, actor: CurrentPrincipal, use_case: Annotated[RequestSync, Depends(Stub(RequestSync))]
) -> CreatedOut:
    return CreatedOut(id=await use_case(actor, server_code=body.server_code, kind=body.kind, days=body.days))
