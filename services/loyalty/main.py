"""Точка входа Loyalty Service (порт 8050)."""

from fastapi import FastAPI

from common import health
from common.errors import register_exception_handlers
from loyalty import api


def create_app() -> FastAPI:
    app = FastAPI(
        title="Loyalty Service",
        description="Программа лояльности: статус пользователя и скидка.",
        version="v1",
    )
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(api.router)
    return app


app = create_app()
