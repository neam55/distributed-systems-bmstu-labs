from fastapi import FastAPI

from src.api import health
from src.api.exception_handlers import register_exception_handlers
from src.api.v1 import persons


def create_app() -> FastAPI:
    app = FastAPI(
        title="Person Service",
        description="Лабораторная работа №1: CRUD над сущностью Person.",
        version="v1",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(persons.router)
    return app


app = create_app()
