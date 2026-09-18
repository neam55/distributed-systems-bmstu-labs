"""Трансляция исключений в HTTP-ответы, описанные в person-service.yaml."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.core.exceptions import PersonNotFoundError


async def person_not_found_handler(_: Request, exc: Exception) -> JSONResponse:
    """Доменное «не найдено» -> 404 ErrorResponse."""
    assert isinstance(exc, PersonNotFoundError)
    return JSONResponse(status_code=404, content={"message": str(exc)})


async def validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Ошибка валидации -> 400 ValidationErrorResponse.

    FastAPI по умолчанию отвечает 422, но контракт курса требует 400.
    """
    assert isinstance(exc, RequestValidationError)
    errors: dict[str, str] = {}
    for error in exc.errors():
        location = error.get("loc", ())
        # Первый элемент loc — источник ("body", "path", ...), он не нужен клиенту.
        field = ".".join(str(part) for part in location[1:]) or str(location[0] if location else "request")
        errors.setdefault(field, error.get("msg", "invalid value"))
    return JSONResponse(
        status_code=400,
        content={"message": "Validation failed", "errors": errors},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(PersonNotFoundError, person_not_found_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
