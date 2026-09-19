from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Person
from src.domain.repositories import PersonRepository
from src.infrastructure.persistence.models import PersonORM


class SQLAlchemyPersonRepository(PersonRepository):
    
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[Person]:
        result = await self._session.execute(select(PersonORM).order_by(PersonORM.id))
        return [row.to_domain() for row in result.scalars()]

    async def get(self, person_id: int) -> Person | None:
        row = await self._session.get(PersonORM, person_id)
        return row.to_domain() if row is not None else None

    async def add(self, person: Person) -> Person:
        row = PersonORM(
            name=person.name,
            age=person.age,
            address=person.address,
            work=person.work,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row.to_domain()

    async def update(self, person_id: int, changes: dict[str, Any]) -> Person | None:
        row = await self._session.get(PersonORM, person_id)
        if row is None:
            return None
        for field, value in changes.items():
            setattr(row, field, value)
        await self._session.commit()
        await self._session.refresh(row)
        return row.to_domain()

    async def delete(self, person_id: int) -> bool:
        row = await self._session.get(PersonORM, person_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True
