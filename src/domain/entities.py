"""Сущности предметной области.

Намеренно не зависят ни от SQLAlchemy, ни от Pydantic: домен не должен знать,
как его сохраняют и как сериализуют наружу.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class Person:
    """Человек — центральная сущность сервиса."""

    name: str
    id: int | None = None
    age: int | None = None
    address: str | None = None
    work: str | None = None
