from dataclasses import replace
from typing import Any

from src.domain.entities import Person
from src.domain.repositories import PersonRepository


class InMemoryPersonRepository(PersonRepository):

    def __init__(self) -> None:
        self._storage: dict[int, Person] = {}
        self._next_id = 1

    async def list_all(self) -> list[Person]:
        return [replace(person) for person in self._storage.values()]

    async def get(self, person_id: int) -> Person | None:
        person = self._storage.get(person_id)
        return replace(person) if person is not None else None

    async def add(self, person: Person) -> Person:
        stored = replace(person, id=self._next_id)
        self._storage[self._next_id] = stored
        self._next_id += 1
        return replace(stored)

    async def update(self, person_id: int, changes: dict[str, Any]) -> Person | None:
        person = self._storage.get(person_id)
        if person is None:
            return None
        updated = replace(person, **changes)
        self._storage[person_id] = updated
        return replace(updated)

    async def delete(self, person_id: int) -> bool:
        return self._storage.pop(person_id, None) is not None
