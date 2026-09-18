"""Сервисный слой: бизнес-правила поверх абстрактного хранилища."""

from typing import Any

from src.core.exceptions import PersonNotFoundError
from src.domain.entities import Person
from src.domain.repositories import PersonRepository


class PersonService:
    """Операции над записями о людях.

    Зависит от абстракции PersonRepository, а не от конкретной БД, поэтому
    тестируется без Postgres и переживает смену хранилища без правок.
    """

    def __init__(self, repository: PersonRepository) -> None:
        self._repository = repository

    async def list_persons(self) -> list[Person]:
        return await self._repository.list_all()

    async def get_person(self, person_id: int) -> Person:
        person = await self._repository.get(person_id)
        if person is None:
            raise PersonNotFoundError(person_id)
        return person

    async def create_person(self, person: Person) -> Person:
        return await self._repository.add(person)

    async def update_person(self, person_id: int, changes: dict[str, Any]) -> Person:
        person = await self._repository.update(person_id, changes)
        if person is None:
            raise PersonNotFoundError(person_id)
        return person

    async def delete_person(self, person_id: int) -> None:
        if not await self._repository.delete(person_id):
            raise PersonNotFoundError(person_id)
