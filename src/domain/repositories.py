"""Порт хранилища (DIP): сервисный слой зависит только от этой абстракции."""

from abc import ABC, abstractmethod
from typing import Any

from src.domain.entities import Person


class PersonRepository(ABC):
    """Контракт хранилища записей о людях.

    Реализации: SQLAlchemyPersonRepository (Postgres) и InMemoryPersonRepository
    (тесты). Методы возвращают None / False вместо исключений — трактовка
    «не найдено» как ошибки принадлежит сервисному слою, а не хранилищу.
    """

    @abstractmethod
    async def list_all(self) -> list[Person]:
        """Вернуть все записи."""

    @abstractmethod
    async def get(self, person_id: int) -> Person | None:
        """Вернуть запись по id или None, если её нет."""

    @abstractmethod
    async def add(self, person: Person) -> Person:
        """Сохранить новую запись и вернуть её с присвоенным id."""

    @abstractmethod
    async def update(self, person_id: int, changes: dict[str, Any]) -> Person | None:
        """Частично обновить запись. None, если записи нет."""

    @abstractmethod
    async def delete(self, person_id: int) -> bool:
        """Удалить запись. False, если её не было."""
