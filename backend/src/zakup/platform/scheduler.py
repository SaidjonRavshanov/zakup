"""Kunlik ishlar (worker): "har kuni soat N dan keyin bir marta" — Toshkent vaqti bo'yicha.

Bir nechta worker bo'lsa ham bitta marta: `platform.daily_jobs` (job, day) PK — birinchi INSERT yutadi.
Worker kech ishga tushsa (masalan, 14:00) — o'sha kunning ishi darhol bajariladi (catch-up).
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, timedelta

import structlog
from sqlalchemy import Column, Date, DateTime, Table, Text, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from zakup.platform.db import metadata
from zakup.shared_kernel.clock import Clock, utc_now

log = structlog.get_logger()
TASHKENT_OFFSET = timedelta(hours=5)

daily_jobs = Table(
    "daily_jobs",
    metadata,
    Column("job", Text, primary_key=True),
    Column("day", Date, primary_key=True),
    Column("ran_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="platform",
)


@dataclass(frozen=True, slots=True)
class DailyJob:
    name: str
    hour: int | None  # None — o'chirilgan
    run: Callable[[], Awaitable[object]]


class DailyScheduler:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], jobs: list[DailyJob], clock: Clock = utc_now
    ) -> None:
        self._sessions = session_factory
        self._jobs = jobs
        self._clock = clock
        self._done: dict[str, date] = {}  # xotirada: har aylanishda bazaga bormaslik uchun

    async def __call__(self) -> bool:
        """True — biror ish bajarildi."""
        local = self._clock() + TASHKENT_OFFSET
        ran = False
        for job in self._jobs:
            if job.hour is None or local.hour < job.hour or self._done.get(job.name) == local.date():
                continue
            self._done[job.name] = local.date()
            if not await self._claim(job.name, local.date()):
                continue  # boshqa worker bajargan
            log.info("daily_job_started", job=job.name)
            try:
                await job.run()
            except Exception:  # worker yiqilmasin
                log.exception("daily_job_failed", job=job.name)
            ran = True
        return ran

    async def _claim(self, name: str, day: date) -> bool:
        async with self._sessions() as session:
            claimed = await session.scalar(
                insert(daily_jobs).values(job=name, day=day).on_conflict_do_nothing().returning(daily_jobs.c.job)
            )
            await session.commit()
        return claimed is not None
