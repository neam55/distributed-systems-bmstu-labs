from uuid import uuid4

from httpx import AsyncClient

HEADERS = {"X-User-Name": "Test Max"}


async def test_reverse_increment_applies_once(client: AsyncClient) -> None:
    uid = str(uuid4())
    await client.patch("/api/v1/loyalty", headers=HEADERS, json={"delta": 1, "operationUid": uid})
    for _ in range(2):
        response = await client.post(f"/api/v1/loyalty/operations/{uid}/reverse", headers=HEADERS)
        assert response.status_code == 200
        assert response.json()["reservationCount"] == 25


async def test_reverse_before_increment_prevents_late_increment(client: AsyncClient) -> None:
    uid = str(uuid4())
    response = await client.post(f"/api/v1/loyalty/operations/{uid}/reverse", headers=HEADERS)
    assert response.status_code == 200
    response = await client.patch("/api/v1/loyalty", headers=HEADERS, json={"delta": 1, "operationUid": uid})
    assert response.json()["reservationCount"] == 25
