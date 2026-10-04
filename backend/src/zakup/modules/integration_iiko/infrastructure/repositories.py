from typing import Any
from uuid import UUID

from sqlalchemy import exists, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from zakup.modules.integration_iiko.application.ports import EntityKind, SyncKind, SyncRun, SyncRunItem, SyncStatus
from zakup.modules.integration_iiko.infrastructure.tables import links, sync_runs
from zakup.shared_kernel.ids import new_id


class SqlLinks:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def local_id(self, server: str, kind: EntityKind, iiko_id: UUID) -> UUID | None:
        query = select(links.c.local_id).where(
            links.c.server_code == server, links.c.kind == kind.value, links.c.iiko_id == iiko_id
        )
        result: UUID | None = await self._session.scalar(query)
        return result

    async def local_id_any_server(self, kind: EntityKind, iiko_id: UUID) -> UUID | None:
        query = select(links.c.local_id).where(links.c.kind == kind.value, links.c.iiko_id == iiko_id).limit(1)
        result: UUID | None = await self._session.scalar(query)
        return result

    async def local_id_by_key(self, kind: EntityKind, key: str) -> UUID | None:
        query = select(links.c.local_id).where(links.c.kind == kind.value, links.c.key == key).limit(1)
        result: UUID | None = await self._session.scalar(query)
        return result

    async def mapping(self, server: str, kind: EntityKind) -> dict[UUID, UUID]:
        query = select(links.c.iiko_id, links.c.local_id).where(
            links.c.server_code == server, links.c.kind == kind.value
        )
        return {row.iiko_id: row.local_id for row in (await self._session.execute(query)).all()}

    async def iiko_ids(self, server: str, kind: EntityKind, local_id: UUID) -> list[tuple[UUID, dict[str, Any]]]:
        query = (
            select(links.c.iiko_id, links.c.attrs)
            .where(links.c.server_code == server, links.c.kind == kind.value, links.c.local_id == local_id)
            .order_by(links.c.updated_at.desc())
        )
        return [(row.iiko_id, row.attrs) for row in await self._session.execute(query)]

    async def save(
        self,
        server: str,
        kind: EntityKind,
        iiko_id: UUID,
        local_id: UUID,
        *,
        key: str | None = None,
        attrs: dict[str, Any] | None = None,
    ) -> None:
        values = {"local_id": local_id, "key": key, "attrs": attrs or {}, "updated_at": func.now()}
        statement = insert(links).values(server_code=server, kind=kind.value, iiko_id=iiko_id, **values)
        await self._session.execute(
            statement.on_conflict_do_update(index_elements=["server_code", "kind", "iiko_id"], set_=values)
        )


class SqlSyncRuns:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(
        self, *, server_code: str, kind: SyncKind, params: dict[str, Any], requested_by: UUID | None
    ) -> UUID:
        run_id = new_id()
        await self._session.execute(
            insert(sync_runs).values(
                id=run_id, server_code=server_code, kind=kind.value, params=params, requested_by=requested_by
            )
        )
        return run_id

    async def has_pending(self, server_code: str, kind: SyncKind) -> bool:
        condition = (
            (sync_runs.c.server_code == server_code)
            & (sync_runs.c.kind == kind.value)
            & sync_runs.c.status.in_([SyncStatus.QUEUED.value, SyncStatus.RUNNING.value])
        )
        return bool(await self._session.scalar(select(exists().where(condition))))

    async def claim_next(self) -> SyncRun | None:
        query = (
            select(sync_runs.c.id, sync_runs.c.server_code, sync_runs.c.kind, sync_runs.c.params)
            .where(sync_runs.c.status == SyncStatus.QUEUED.value)
            .order_by(sync_runs.c.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        row = (await self._session.execute(query)).first()
        if row is None:
            return None
        await self._session.execute(
            update(sync_runs)
            .where(sync_runs.c.id == row.id)
            .values(status=SyncStatus.RUNNING.value, started_at=func.now())
        )
        return SyncRun(row.id, row.server_code, SyncKind(row.kind), SyncStatus.RUNNING, row.params)

    async def finish(self, run_id: UUID, *, stats: dict[str, int], error: str | None) -> None:
        status = SyncStatus.FAILED if error else SyncStatus.DONE
        await self._session.execute(
            update(sync_runs)
            .where(sync_runs.c.id == run_id)
            .values(status=status.value, stats=stats, error=error, finished_at=func.now())
        )


class SqlSyncRunReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def recent(self, *, limit: int) -> list[SyncRunItem]:
        query = select(sync_runs).order_by(sync_runs.c.created_at.desc()).limit(limit)
        rows = (await self._session.execute(query)).all()
        return [
            SyncRunItem(
                id=row.id,
                server_code=row.server_code,
                kind=SyncKind(row.kind),
                status=SyncStatus(row.status),
                params=row.params,
                stats=row.stats,
                error=row.error,
                created_at=row.created_at,
                started_at=row.started_at,
                finished_at=row.finished_at,
            )
            for row in rows
        ]
