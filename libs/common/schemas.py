"""Базовые схемы транспортного слоя, общие для всех сервисов."""

from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

# Описания дополнительных ответов для декораторов FastAPI.
type Responses = dict[int | str, dict[str, Any]]


class CamelModel(BaseModel):
    """Модель, которая сериализуется в camelCase, а принимает оба написания.

    Контракт системы (OpenAPI варианта 2) целиком в camelCase, при этом python-код
    и колонки БД остаются в snake_case.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ErrorResponse(BaseModel):
    """Ответ об ошибке без детализации по полям."""

    message: str


class ErrorDescription(BaseModel):
    """Описание ошибки в одном поле запроса."""

    field: str
    error: str


class ValidationErrorResponse(BaseModel):
    """Ответ об ошибке валидации: сообщение и массив полей с описанием."""

    message: str
    errors: list[ErrorDescription]
