"""Точка входа Reservation Service (порт 8070)."""

from fastapi import FastAPI

from common import health
from common.errors import register_exception_handlers
from reservation import api


def create_app() -> FastAPI:
    app = FastAPI(
        title="Reservation Service",
        description="Справочник отелей и бронирования пользователей.",
        version="v1",
    )
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(api.hotels_router)
    app.include_router(api.reservations_router)
    return app


app = create_app()
