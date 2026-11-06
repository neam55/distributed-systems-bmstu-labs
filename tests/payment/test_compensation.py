from uuid import uuid4

from httpx import AsyncClient


async def test_create_is_idempotent_and_conflicting_price_is_rejected(client: AsyncClient) -> None:
    uid = str(uuid4())
    payload = {"paymentUid": uid, "price": 100}
    first = await client.post("/api/v1/payments", json=payload)
    second = await client.post("/api/v1/payments", json=payload)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    conflict = await client.post("/api/v1/payments", json={**payload, "price": 200})
    assert conflict.status_code == 409


async def test_compensation_prevents_late_activation(client: AsyncClient) -> None:
    uid = str(uuid4())
    for _ in range(2):
        assert (await client.post(f"/api/v1/payments/{uid}/compensate")).status_code == 204
    result = await client.post("/api/v1/payments", json={"paymentUid": uid, "price": 100})
    assert result.status_code == 201
    assert result.json()["status"] == "CANCELED"
