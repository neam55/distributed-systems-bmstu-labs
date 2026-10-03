"""Контракт ответов об ошибках и сериализация в camelCase."""

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from common.errors import NotFoundError, UpstreamError, ValidationError, register_exception_handlers
from common.schemas import CamelModel


class SampleModel(CamelModel):
    reservation_count: int
    full_address: str


class SampleRequest(CamelModel):
    start_date: str


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/not-found")
    async def not_found() -> None:
        raise NotFoundError("Hotel with uid 1 not found")

    @app.get("/invalid")
    async def invalid() -> None:
        raise ValidationError("Validation failed", {"endDate": "endDate must be later than startDate"})

    @app.get("/unavailable")
    async def unavailable() -> None:
        raise UpstreamError("Payment", "connection refused")

    @app.post("/echo")
    async def echo(payload: SampleRequest) -> SampleRequest:
        return payload

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


def test_camel_model_serializes_to_camel_case() -> None:
    model = SampleModel(reservation_count=25, full_address="Россия, Москва")

    assert model.model_dump(by_alias=True) == {
        "reservationCount": 25,
        "fullAddress": "Россия, Москва",
    }


def test_camel_model_accepts_both_spellings() -> None:
    from_camel = SampleModel.model_validate({"reservationCount": 1, "fullAddress": "a"})
    from_snake = SampleModel(reservation_count=1, full_address="a")

    assert from_camel == from_snake


async def test_domain_not_found_is_404_error_response(client: AsyncClient) -> None:
    response = await client.get("/not-found")

    assert response.status_code == 404
    assert response.json() == {"message": "Hotel with uid 1 not found"}


async def test_domain_validation_is_400_with_errors_array(client: AsyncClient) -> None:
    response = await client.get("/invalid")

    assert response.status_code == 400
    assert response.json() == {
        "message": "Validation failed",
        "errors": [{"field": "endDate", "error": "endDate must be later than startDate"}],
    }


async def test_unavailable_upstream_is_503(client: AsyncClient) -> None:
    response = await client.get("/unavailable")

    assert response.status_code == 503
    assert "Payment" in response.json()["message"]


async def test_request_validation_error_is_400_not_422(client: AsyncClient) -> None:
    response = await client.post("/echo", json={})

    assert response.status_code == 400
    body = response.json()
    assert body["message"] == "Validation failed"
    assert [error["field"] for error in body["errors"]] == ["startDate"]
