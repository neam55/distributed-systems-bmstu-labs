from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from loyalty.dependencies import get_loyalty_repository
from loyalty.entities import Loyalty, LoyaltyStatus
from loyalty.main import create_app
from loyalty.repository import LoyaltyRepository
from loyalty.service import LoyaltyService
from tests.loyalty.fakes import InMemoryLoyaltyRepository

TEST_USER = "Test Max"


@pytest.fixture
def repository() -> LoyaltyRepository:
    """Хранилище с тестовым пользователем приёмочной коллекции."""
    return InMemoryLoyaltyRepository(
        [
            Loyalty(
                username=TEST_USER,
                reservation_count=25,
                status=LoyaltyStatus.GOLD,
                discount=10,
            )
        ]
    )


@pytest.fixture
def service(repository: LoyaltyRepository) -> LoyaltyService:
    return LoyaltyService(repository)


@pytest.fixture
async def client(repository: LoyaltyRepository) -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_loyalty_repository] = lambda: repository
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()
