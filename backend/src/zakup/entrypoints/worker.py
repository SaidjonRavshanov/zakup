"""Fon ishlari: `python -m zakup.entrypoints.worker`.

Hozircha — iiko sinxronizatsiya navbati (iiko.sync_runs). iiko bilan faqat shu process gaplashadi (ADR-05);
bir nechta worker ishga tushirilsa ham har serverga bitta sessiya — PostgreSQL advisory lock.
"""

import asyncio
import contextlib
import signal

import structlog

from zakup.bootstrap import build_iiko_gateway, iiko_scope_factory
from zakup.modules.integration_iiko.application.runs import RunNextSync
from zakup.platform.db import create_engine, create_session_factory
from zakup.platform.logging import configure_logging
from zakup.settings import get_settings

POLL_INTERVAL_S = 5.0
log = structlog.get_logger()


async def main() -> None:
    settings = get_settings()
    configure_logging(json=settings.env == "production")
    engine = create_engine(settings)
    run_next = RunNextSync(build_iiko_gateway(settings, engine), iiko_scope_factory(create_session_factory(engine)))

    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):  # Windows: add_signal_handler yo'q
            asyncio.get_running_loop().add_signal_handler(sig, stop.set)

    log.info("worker_started", iiko_servers=[s.code for s in settings.iiko_servers])
    try:
        while not stop.is_set():
            if not await run_next():
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), POLL_INTERVAL_S)
    finally:
        await engine.dispose()
        log.info("worker_stopped")


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
