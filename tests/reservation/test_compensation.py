from uuid import uuid4

from httpx import AsyncClient

HOTEL = "049161bb-badd-4fa8-9d90-87c9a82b0668"


async def test_late_create_remains_canceled_and_repeated_create_is_identical(client: AsyncClient) -> None:
    uid = str(uuid4())
    headers = {"X-User-Name": "Test Max"}
    route = f"/api/v1/reservations/{uid}/compensate"
    assert (await client.post(route, headers=headers)).status_code == 204
    payload = {
        "reservationUid": uid,
        "username": "Test Max",
        "paymentUid": str(uuid4()),
        "hotelUid": HOTEL,
        "startDate": "2026-01-01",
        "endDate": "2026-01-02",
    }
    first = await client.post("/api/v1/reservations", json=payload)
    second = await client.post("/api/v1/reservations", json=payload)
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert first.json()["status"] == "CANCELED"
    conflict = await client.post("/api/v1/reservations", json={**payload, "endDate": "2026-01-03"})
    assert conflict.status_code == 409


async def test_compensation_cannot_claim_another_users_uid(client: AsyncClient) -> None:
    uid = str(uuid4())
    route = f"/api/v1/reservations/{uid}/compensate"
    assert (await client.post(route, headers={"X-User-Name": "Test Max"})).status_code == 204
    assert (await client.post(route, headers={"X-User-Name": "Other"})).status_code == 404
