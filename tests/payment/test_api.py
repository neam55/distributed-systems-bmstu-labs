from uuid import uuid4

from httpx import AsyncClient


async def test_create_payment_returns_201_with_contract(client: AsyncClient) -> None:
    response = await client.post("/api/v1/payments", json={"price": 27000})

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PAID"
    assert body["price"] == 27000
    assert body["paymentUid"]


async def test_get_payment_by_uid(client: AsyncClient) -> None:
    created = (await client.post("/api/v1/payments", json={"price": 27000})).json()

    response = await client.get(f"/api/v1/payments/{created['paymentUid']}")

    assert response.status_code == 200
    assert response.json() == created


async def test_get_missing_payment_returns_404_error_response(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/payments/{uuid4()}")

    assert response.status_code == 404
    assert "message" in response.json()


async def test_cancel_payment(client: AsyncClient) -> None:
    created = (await client.post("/api/v1/payments", json={"price": 27000})).json()

    response = await client.post(f"/api/v1/payments/{created['paymentUid']}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELED"


async def test_batch_endpoint_returns_requested_payments(client: AsyncClient) -> None:
    first = (await client.post("/api/v1/payments", json={"price": 100})).json()
    second = (await client.post("/api/v1/payments", json={"price": 200})).json()

    response = await client.get(
        "/api/v1/payments", params={"uids": [first["paymentUid"], second["paymentUid"]]}
    )

    assert response.status_code == 200
    assert [item["price"] for item in response.json()] == [100, 200]


async def test_negative_price_is_rejected(client: AsyncClient) -> None:
    response = await client.post("/api/v1/payments", json={"price": -1})

    assert response.status_code == 400
    assert [error["field"] for error in response.json()["errors"]] == ["price"]


async def test_health_is_up(client: AsyncClient) -> None:
    assert (await client.get("/manage/health")).json() == {"status": "UP"}
