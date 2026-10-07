"""Fon ishlari: `python -m zakup.entrypoints.worker`.

Har aylanishda: kunlik ishlar (ertalab iiko sinxroni, avto-zayavka), outbox relay (eventlar → modul reaksiyalari),
bot xabarlari (bittadan), iiko sinxronizatsiya navbati, qabul → iiko kirimi.
iiko bilan faqat shu process gaplashadi (ADR-05); bir nechta worker bo'lsa ham serverga bitta sessiya — advisory lock.
"""

import asyncio
import contextlib
import signal

import structlog

from zakup.bootstrap import (
    build_daily_scheduler,
    build_iiko_gateway,
    build_invoice_exporter,
    build_notification_sender,
    iiko_scope_factory,
    outbox_handlers,
)
from zakup.modules.integration_iiko.application.runs import RunNextSync
from zakup.platform.db import create_engine, create_session_factory
from zakup.platform.logging import configure_logging
from zakup.platform.outbox_relay import OutboxRelay
from zakup.settings import get_settings

POLL_INTERVAL_S = 5.0
log = structlog.get_logger()


async def main() -> None:
    settings = get_settings()
    configure_logging(json=settings.env == "production")
    engine = create_engine(settings)
    sessions = create_session_factory(engine)
    gateway = build_iiko_gateway(settings, engine)
    relay = OutboxRelay(sessions, outbox_handlers(settings))
    send_next = build_notification_sender(settings, sessions)
    run_next = RunNextSync(gateway, iiko_scope_factory(sessions))
    export_next = build_invoice_exporter(settings, gateway, sessions)
    daily = build_daily_scheduler(settings, gateway, sessions)

    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):  # Windows: add_signal_handler yo'q
            asyncio.get_running_loop().add_signal_handler(sig, stop.set)

    log.info("worker_started", iiko_servers=[s.code for s in settings.iiko_servers])
    try:
        while not stop.is_set():
            busy = await daily() | bool(await relay()) | await send_next() | await run_next() | await export_next()
            if not busy:
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), POLL_INTERVAL_S)
    finally:
        await engine.dispose()
        log.info("worker_stopped")


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
