from typing import Any
from uuid import uuid4

from httpx import AsyncClient

from .conftest import ARARAT_FULL_ADDRESS, ARARAT_UID, TEST_USER

USER = {"X-User-Name": TEST_USER}


async def create_reservation(client: AsyncClient, username: str = TEST_USER) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/reservations",
        json={
            "username": username,
            "paymentUid": str(uuid4()),
            "hotelUid": str(ARARAT_UID),
            "startDate": "2021-10-08",
            "endDate": "2021-10-11",
        },
    )
    assert response.status_code == 201
    return response.json()


async def test_hotels_page_matches_contract(client: AsyncClient) -> None:
    response = await client.get("/api/v1/hotels", params={"page": 1, "size": 10})

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["pageSize"] <= 10
    assert body["totalElements"] == 3
    assert body["items"][0] == {
        "hotelUid": str(ARARAT_UID),
        "name": "Ararat Park Hyatt Moscow",
        "country": "Россия",
        "city": "Москва",
        "address": "Неглинная ул., 4",
        "stars": 5,
        "price": 10000,
    }


async def test_size_above_limit_is_rejected(client: AsyncClient) -> None:
    response = await client.get("/api/v1/hotels", params={"page": 1, "size": 1000})

    assert response.status_code == 400


async def test_reservation_dates_are_returned_as_plain_dates(client: AsyncClient) -> None:
    created = await create_reservation(client)

    assert created["startDate"] == "2021-10-08"
    assert created["endDate"] == "2021-10-11"
    assert created["status"] == "PAID"
    assert created["hotel"]["fullAddress"] == ARARAT_FULL_ADDRESS


async def test_get_reservation_by_uid(client: AsyncClient) -> None:
    created = await create_reservation(client)

    response = await client.get(f"/api/v1/reservations/{created['reservationUid']}", headers=USER)

    assert response.status_code == 200
    assert response.json() == created


async def test_reservation_of_another_user_returns_404(client: AsyncClient) -> None:
    created = await create_reservation(client, username="Someone Else")

    response = await client.get(f"/api/v1/reservations/{created['reservationUid']}", headers=USER)

    assert response.status_code == 404
    assert "message" in response.json()


async def test_booking_unknown_hotel_returns_404(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/reservations",
        json={
            "username": TEST_USER,
            "paymentUid": str(uuid4()),
            "hotelUid": str(uuid4()),
            "startDate": "2021-10-08",
            "endDate": "2021-10-11",
        },
    )

    assert response.status_code == 404


async def test_cancel_returns_canceled_reservation(client: AsyncClient) -> None:
    created = await create_reservation(client)

    response = await client.post(f"/api/v1/reservations/{created['reservationUid']}/cancel", headers=USER)

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELED"


async def test_health_is_up(client: AsyncClient) -> None:
    assert (await client.get("/manage/health")).json() == {"status": "UP"}


async def test_page_zero_returns_first_page(client: AsyncClient) -> None:
    response = await client.get("/api/v1/hotels", params={"page": 0, "size": 1})

    assert response.status_code == 200
    assert response.json()["page"] == 0
    assert response.json()["items"][0]["hotelUid"] == str(ARARAT_UID)


async def test_compensated_creation_is_not_a_user_cancellable_booking(client: AsyncClient) -> None:
    from uuid import uuid4

    uid = uuid4()
    payload = {
        "reservationUid": str(uid),
        "username": "Test Max",
        "paymentUid": str(uuid4()),
        "hotelUid": "049161bb-badd-4fa8-9d90-87c9a82b0668",
        "startDate": "2021-10-08",
        "endDate": "2021-10-11",
    }
    headers = {"X-User-Name": "Test Max"}
    assert (await client.post("/api/v1/reservations", json=payload)).status_code == 201
    assert (await client.post(f"/api/v1/reservations/{uid}/compensate", headers=headers)).status_code == 204
    assert (await client.get("/api/v1/reservations", headers=headers)).json() == []
    assert (await client.get(f"/api/v1/reservations/{uid}", headers=headers)).status_code == 404
    assert (await client.post(f"/api/v1/reservations/{uid}/cancel", headers=headers)).status_code == 404
