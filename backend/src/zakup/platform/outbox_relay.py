"""Outbox relay (ADR-04): worker platform.outbox'dagi eventlarni o'qib, modul handler'lariga beradi.

Handler eventni yozgan tranzaksiyadan **keyin**, alohida tranzaksiyada ishlaydi; xatoda — kechikish bilan qayta.
Handler'i yo'q event "qayta ishlandi" deb belgilanadi (kelajakdagi obunachilar uchun saqlanib qoladi).
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from zakup.platform.outbox import outbox

log = structlog.get_logger()
Handler = Callable[[AsyncSession, dict[str, Any]], Awaitable[None]]
MAX_BACKOFF = timedelta(hours=1)


class OutboxRelay:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], handlers: dict[str, Handler]) -> None:
        self._session_factory = session_factory
        self._handlers = handlers

    async def __call__(self, batch: int = 50) -> int:
        """Qayta ishlangan eventlar soni."""
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            query = (
                select(outbox.c.id, outbox.c.event_type, outbox.c.payload, outbox.c.attempts)
                .where(outbox.c.processed_at.is_(None), outbox.c.next_attempt_at <= now)
                .order_by(outbox.c.created_at)
                .limit(batch)
                .with_for_update(skip_locked=True)
            )
            rows = (await session.execute(query)).all()
            for row in rows:
                await self._dispatch(
                    session,
                    event_id=row.id,
                    event_type=row.event_type,
                    payload=row.payload,
                    attempts=row.attempts,
                    now=now,
                )
            await session.commit()
            return len(rows)

    async def _dispatch(
        self,
        session: AsyncSession,
        *,
        event_id: Any,
        event_type: str,
        payload: dict[str, Any],
        attempts: int,
        now: datetime,
    ) -> None:
        handler = self._handlers.get(event_type)
        try:
            if handler is not None:
                async with session.begin_nested():
                    await handler(session, payload)
        except Exception as exc:
            log.warning("outbox_handler_failed", event_type=event_type, error=str(exc))
            delay = min(timedelta(seconds=30 * 2**attempts), MAX_BACKOFF)
            await session.execute(
                update(outbox)
                .where(outbox.c.id == event_id)
                .values(attempts=attempts + 1, next_attempt_at=now + delay, last_error=str(exc)[:1000])
            )
            return
        await session.execute(update(outbox).where(outbox.c.id == event_id).values(processed_at=now))
