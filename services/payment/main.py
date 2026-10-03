"""Точка входа Payment Service (порт 8060)."""

from fastapi import FastAPI

from common import health
from common.errors import register_exception_handlers
from payment import api


def create_app() -> FastAPI:
    app = FastAPI(
        title="Payment Service",
        description="Операции оплаты бронирований.",
        version="v1",
    )
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(api.router)
    return app


app = create_app()
