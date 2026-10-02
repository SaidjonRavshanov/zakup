from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from zakup import __version__
from zakup.platform.di import Stub

router = APIRouter(tags=["system"])


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "down"]
    version: str


@router.get("/health")
async def health(engine: Annotated[AsyncEngine, Depends(Stub(AsyncEngine))]) -> HealthOut:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        database: Literal["ok", "down"] = "ok"
    except Exception:  # health hech qachon yiqilmasligi kerak
        database = "down"
    return HealthOut(status="ok" if database == "ok" else "degraded", database=database, version=__version__)
