from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from payment.dependencies import get_payment_repository
from payment.main import create_app
from payment.repository import PaymentRepository
from payment.service import PaymentService
from tests.payment.fakes import InMemoryPaymentRepository


@pytest.fixture
def repository() -> PaymentRepository:
    return InMemoryPaymentRepository()


@pytest.fixture
def service(repository: PaymentRepository) -> PaymentService:
    return PaymentService(repository)


@pytest.fixture
async def client(repository: PaymentRepository) -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_payment_repository] = lambda: repository
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    app.dependency_overrides.clear()
