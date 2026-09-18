from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import get_person_repository
from src.domain.repositories import PersonRepository
from src.domain.services import PersonService
from src.main import create_app
from tests.fakes import InMemoryPersonRepository


@pytest.fixture
def repository() -> PersonRepository:
    return InMemoryPersonRepository()


@pytest.fixture
def service(repository: PersonRepository) -> PersonService:
    return PersonService(repository)


@pytest.fixture
async def client(repository: PersonRepository) -> AsyncIterator[AsyncClient]:
    """Приложение с подменённым хранилищем — без Postgres и без сети."""
    app = create_app()
    app.dependency_overrides[get_person_repository] = lambda: repository
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()
