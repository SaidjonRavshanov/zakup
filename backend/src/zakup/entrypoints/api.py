"""HTTP API entrypoint: `uvicorn zakup.entrypoints.api:app`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from zakup import __version__
from zakup.bootstrap import ROUTERS, wire
from zakup.platform.db import create_engine, create_session_factory
from zakup.platform.http_errors import register_error_handlers
from zakup.platform.logging import configure_logging
from zakup.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(json=settings.env == "production")
    engine = create_engine(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await engine.dispose()

    app = FastAPI(
        title="Zakup API",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.env != "production" else None,
        openapi_url="/api/openapi.json" if settings.env != "production" else None,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    for router in ROUTERS:
        app.include_router(router, prefix="/api/v1")
    wire(app, engine, create_session_factory(engine), settings)
    return app


app = create_app()
