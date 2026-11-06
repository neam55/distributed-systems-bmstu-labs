"""Точка входа Gateway Service (порт 8080)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from common import health
from common.errors import register_exception_handlers
from gateway import api
from gateway.dependencies import close_http_clients, create_recovery_queue


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    recovery = create_recovery_queue(app)
    app.state.recovery = recovery
    recovery.start()
    try:
        yield
    finally:
        await recovery.stop()
        await close_http_clients(app)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Hotels Booking System",
        description="Gateway: единая точка входа и оркестрация сервисов системы.",
        version="v1",
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(api.router)
    return app


app = create_app()
