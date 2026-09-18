"""Сборка графа зависимостей для HTTP-слоя."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.repositories import PersonRepository
from src.domain.services import PersonService
from src.infrastructure.persistence.database import get_session
from src.infrastructure.persistence.repository import SQLAlchemyPersonRepository


def get_person_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PersonRepository:
    """Единственная точка, где выбирается конкретная реализация хранилища.

    В тестах подменяется через app.dependency_overrides.
    """
    return SQLAlchemyPersonRepository(session)


def get_person_service(
    repository: Annotated[PersonRepository, Depends(get_person_repository)],
) -> PersonService:
    return PersonService(repository)


PersonServiceDep = Annotated[PersonService, Depends(get_person_service)]
