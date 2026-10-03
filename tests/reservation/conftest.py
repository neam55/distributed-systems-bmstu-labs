from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from reservation.dependencies import get_reservation_repository
from reservation.entities import Hotel
from reservation.main import create_app
from reservation.repository import ReservationRepository
from reservation.service import ReservationService
from tests.reservation.fakes import InMemoryReservationRepository

TEST_USER = "Test Max"
ARARAT_UID = UUID("049161bb-badd-4fa8-9d90-87c9a82b0668")
ARARAT_FULL_ADDRESS = "Россия, Москва, Неглинная ул., 4"


@pytest.fixture
def hotels() -> list[Hotel]:
    """Отель приёмочной коллекции и ещё два — чтобы проверить пагинацию."""
    return [
        Hotel(
            hotel_uid=ARARAT_UID,
            name="Ararat Park Hyatt Moscow",
            country="Россия",
            city="Москва",
            address="Неглинная ул., 4",
            stars=5,
            price=10000,
        ),
        Hotel(
            hotel_uid=UUID("6ce14b26-6ea0-4b53-9bba-4f0b9fcd2c6f"),
            name="Radisson Slavyanskaya",
            country="Россия",
            city="Москва",
            address="пл. Европы, 2",
            stars=4,
            price=8000,
        ),
        Hotel(
            hotel_uid=UUID("f1b7d4a3-5c2e-4f6a-8d9b-1e3c5a7b9d0f"),
            name="Astoria",
            country="Россия",
            city="Санкт-Петербург",
            address="Большая Морская ул., 39",
            stars=5,
            price=12000,
        ),
    ]


@pytest.fixture
def repository(hotels: list[Hotel]) -> ReservationRepository:
    return InMemoryReservationRepository(hotels)


@pytest.fixture
def service(repository: ReservationRepository) -> ReservationService:
    return ReservationService(repository)


@pytest.fixture
async def client(repository: ReservationRepository) -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_reservation_repository] = lambda: repository
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()
