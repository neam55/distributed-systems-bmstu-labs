"""Pydantic-схемы транспортного слоя (DTO), соответствуют person-service.yaml."""

from pydantic import BaseModel, ConfigDict, Field


class PersonRequest(BaseModel):
    """Тело запроса на создание записи: name обязателен."""

    name: str = Field(min_length=1, max_length=255, examples=["Ivan Ivanov"])
    age: int | None = Field(default=None, ge=0, le=150, examples=[31])
    address: str | None = Field(default=None, max_length=255, examples=["Moscow, Baumanskaya 5"])
    work: str | None = Field(default=None, max_length=255, examples=["BMSTU"])


class PersonUpdateRequest(BaseModel):
    """Тело запроса на частичное обновление: все поля опциональны.

    Незаданные поля не попадают в model_dump(exclude_unset=True) и потому
    сохраняют прежние значения в БД.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    age: int | None = Field(default=None, ge=0, le=150)
    address: str | None = Field(default=None, max_length=255)
    work: str | None = Field(default=None, max_length=255)


class PersonResponse(BaseModel):
    """Представление записи в ответах."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int | None = None
    address: str | None = None
    work: str | None = None


class ErrorResponse(BaseModel):
    """Ответ об ошибке без детализации по полям."""

    message: str


class ValidationErrorResponse(BaseModel):
    """Ответ об ошибке валидации: message + пофайловая детализация."""

    message: str
    errors: dict[str, str]
