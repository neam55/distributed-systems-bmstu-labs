"""Исключения предметной области и их трансляция в HTTP-ответы контракта."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from common.schemas import ErrorDescription, ErrorResponse, ValidationErrorResponse


class DomainError(Exception):
    """Базовое исключение предметной области."""


class NotFoundError(DomainError):
    """Запрошенная сущность не найдена (или недоступна текущему пользователю)."""


class ValidationError(DomainError):
    """Данные запроса не проходят проверку бизнес-правил."""

    def __init__(self, message: str, errors: dict[str, str] | None = None) -> None:
        self.message = message
        self.errors = errors or {}
        super().__init__(message)


class UpstreamError(DomainError):
    """Сервис, к которому обратился Gateway, недоступен или ответил ошибкой."""

    def __init__(self, service: str, detail: str) -> None:
        self.service = service
        self.detail = detail
        super().__init__(f"{service} service is unavailable: {detail}")


async def not_found_handler(_: Request, exc: Exception) -> JSONResponse:
    """Доменное «не найдено» -> 404 ErrorResponse."""
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(message=str(exc)).model_dump(),
    )


async def domain_validation_handler(_: Request, exc: Exception) -> JSONResponse:
    """Нарушение бизнес-правила -> 400 ValidationErrorResponse."""
    assert isinstance(exc, ValidationError)
    return JSONResponse(
        status_code=400,
        content=ValidationErrorResponse(
            message=exc.message,
            errors=[ErrorDescription(field=field, error=error) for field, error in exc.errors.items()],
        ).model_dump(),
    )


async def request_validation_handler(_: Request, exc: Exception) -> JSONResponse:
    """Ошибка разбора запроса -> 400 ValidationErrorResponse.

    FastAPI по умолчанию отвечает 422, но контракт курса требует 400.
    """
    assert isinstance(exc, RequestValidationError)
    errors: list[ErrorDescription] = []
    seen: set[str] = set()
    for error in exc.errors():
        location = error.get("loc", ())
        # Первый элемент loc — источник ("body", "query", ...), клиенту он не нужен.
        field = ".".join(str(part) for part in location[1:]) or str(location[0] if location else "request")
        if field in seen:
            continue
        seen.add(field)
        errors.append(ErrorDescription(field=field, error=error.get("msg", "invalid value")))
    return JSONResponse(
        status_code=400,
        content=ValidationErrorResponse(message="Validation failed", errors=errors).model_dump(),
    )


async def upstream_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Недоступный соседний сервис -> 503 ErrorResponse."""
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(message=str(exc)).model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Подключает единый набор обработчиков. Вызывается в фабрике приложения сервиса."""
    app.add_exception_handler(NotFoundError, not_found_handler)
    app.add_exception_handler(ValidationError, domain_validation_handler)
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(UpstreamError, upstream_error_handler)
