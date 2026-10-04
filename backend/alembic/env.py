import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from zakup.modules.catalog.infrastructure import tables as _catalog  # noqa: F401
from zakup.modules.identity.infrastructure import tables as _identity  # noqa: F401
from zakup.modules.integration_iiko.infrastructure import tables as _iiko  # noqa: F401
from zakup.modules.procurement.infrastructure import tables as _procurement  # noqa: F401
from zakup.platform import outbox as _outbox  # noqa: F401 — jadvallarni metadata'ga ro'yxatdan o'tkazish
from zakup.platform.db import SCHEMAS, metadata
from zakup.settings import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata


def include_name(name: str | None, type_: str, _: object) -> bool:
    # Faqat o'zimizning sxemalar (public va boshqa bazalardagi jadvallarni tegmaymiz)
    return name in SCHEMAS if type_ == "schema" else True


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        compare_type=True,
        version_table_schema="platform",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(str(get_settings().database_url))
    async with engine.connect() as connection:
        # version jadvali platform sxemasida — sxema birinchi migratsiyadan oldin kerak
        await connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS platform")
        await connection.commit()
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_offline() -> None:
    context.configure(
        url=str(get_settings().database_url),
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        version_table_schema="platform",
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
