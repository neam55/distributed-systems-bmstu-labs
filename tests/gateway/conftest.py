from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from gateway.clients import HotelData
from gateway.dependencies import get_loyalty_client, get_payment_client, get_reservation_client
from gateway.main import create_app
from gateway.service import BookingService
from tests.gateway.fakes import (
    FakeLoyaltyServiceClient,
    FakePaymentServiceClient,
    FakeReservationServiceClient,
)

TEST_USER = "Test Max"
ARARAT_UID = UUID("049161bb-badd-4fa8-9d90-87c9a82b0668")
ARARAT_FULL_ADDRESS = "Россия, Москва, Неглинная ул., 4"
# 10000 за ночь, 3 ночи, скидка GOLD 10% -> 27000.
EXPECTED_PRICE = 27000


@pytest.fixture
def calls() -> list[str]:
    """Журнал обращений к сервисам в порядке их выполнения."""
    return []


@pytest.fixture
def hotels() -> list[HotelData]:
    return [
        HotelData(
            hotel_uid=ARARAT_UID,
            name="Ararat Park Hyatt Moscow",
            country="Россия",
            city="Москва",
            address="Неглинная ул., 4",
            stars=5,
            price=10000,
        )
    ]


@pytest.fixture
def reservations(hotels: list[HotelData], calls: list[str]) -> FakeReservationServiceClient:
    return FakeReservationServiceClient(hotels, calls)


@pytest.fixture
def payments(calls: list[str]) -> FakePaymentServiceClient:
    return FakePaymentServiceClient(calls)


@pytest.fixture
def loyalty(calls: list[str]) -> FakeLoyaltyServiceClient:
    return FakeLoyaltyServiceClient(calls)


@pytest.fixture
def service(
    reservations: FakeReservationServiceClient,
    payments: FakePaymentServiceClient,
    loyalty: FakeLoyaltyServiceClient,
) -> BookingService:
    return BookingService(reservations, payments, loyalty)


@pytest.fixture
async def client(
    reservations: FakeReservationServiceClient,
    payments: FakePaymentServiceClient,
    loyalty: FakeLoyaltyServiceClient,
) -> AsyncIterator[AsyncClient]:
    """Gateway с подменёнными клиентами: сеть и соседние сервисы не нужны."""
    app = create_app()
    app.dependency_overrides[get_reservation_client] = lambda: reservations
    app.dependency_overrides[get_payment_client] = lambda: payments
    app.dependency_overrides[get_loyalty_client] = lambda: loyalty
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()
