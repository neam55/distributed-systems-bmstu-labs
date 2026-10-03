"""Внешний API Gateway: тесты повторяют приёмочный сценарий v2/postman/collection.json."""

from uuid import uuid4

from httpx import AsyncClient

from .conftest import ARARAT_FULL_ADDRESS, ARARAT_UID, EXPECTED_PRICE, TEST_USER

USER = {"X-User-Name": TEST_USER}
BOOKING = {
    "hotelUid": str(ARARAT_UID),
    "startDate": "2021-10-08",
    "endDate": "2021-10-11",
}


async def test_acceptance_scenario(client: AsyncClient) -> None:
    """Полный проход коллекции: отели -> лояльность -> бронь -> проверки -> отмена."""
    hotels = await client.get("/api/v1/hotels", params={"page": 1, "size": 10})
    assert hotels.status_code == 200
    assert hotels.headers["content-type"].startswith("application/json")
    page = hotels.json()
    assert page["page"] == 1
    assert page["pageSize"] <= 10
    assert page["totalElements"] == 1
    hotel = page["items"][0]
    assert hotel["hotelUid"] == str(ARARAT_UID)
    assert hotel["price"] == 10000

    loyalty = (await client.get("/api/v1/loyalty", headers=USER)).json()
    assert loyalty == {"status": "GOLD", "discount": 10, "reservationCount": 25}

    booked = await client.post("/api/v1/reservations", headers=USER, json=BOOKING)
    assert booked.status_code == 200
    created = booked.json()
    assert created["hotelUid"] == str(ARARAT_UID)
    assert created["startDate"] == "2021-10-08"
    assert created["endDate"] == "2021-10-11"
    assert created["discount"] == 10
    assert created["status"] == "PAID"
    assert created["payment"]["status"] == "PAID"
    assert created["payment"]["price"] == EXPECTED_PRICE
    reservation_uid = created["reservationUid"]

    one = await client.get(f"/api/v1/reservations/{reservation_uid}", headers=USER)
    assert one.status_code == 200
    body = one.json()
    assert body["hotel"]["fullAddress"] == ARARAT_FULL_ADDRESS
    assert body["hotel"]["stars"] == 5
    assert body["startDate"] == "2021-10-08"
    assert body["status"] == "PAID"
    assert body["payment"]["price"] == EXPECTED_PRICE

    everything = await client.get("/api/v1/reservations", headers=USER)
    assert everything.status_code == 200
    assert [item["reservationUid"] for item in everything.json()] == [reservation_uid]

    me = await client.get("/api/v1/me", headers=USER)
    assert me.status_code == 200
    info = me.json()
    assert [item["reservationUid"] for item in info["reservations"]] == [reservation_uid]
    assert info["loyalty"]["discount"] == 10

    after = (await client.get("/api/v1/loyalty", headers=USER)).json()
    assert after["reservationCount"] == loyalty["reservationCount"] + 1

    canceled = await client.delete(f"/api/v1/reservations/{reservation_uid}", headers=USER)
    assert canceled.status_code == 204
    assert canceled.content == b""


async def test_booking_unknown_hotel_returns_404_error_response(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/reservations", headers=USER, json={**BOOKING, "hotelUid": str(uuid4())}
    )

    assert response.status_code == 404
    assert "message" in response.json()


async def test_booking_with_end_date_before_start_returns_400(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/reservations", headers=USER, json={**BOOKING, "endDate": "2021-10-07"}
    )

    assert response.status_code == 400
    body = response.json()
    assert body["message"]
    assert [error["field"] for error in body["errors"]] == ["endDate"]


async def test_booking_with_malformed_date_returns_400(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/reservations", headers=USER, json={**BOOKING, "startDate": "not-a-date"}
    )

    assert response.status_code == 400
    assert [error["field"] for error in response.json()["errors"]] == ["startDate"]


async def test_unknown_reservation_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/v1/reservations/{uuid4()}", headers=USER)

    assert response.status_code == 404


async def test_cancel_unknown_reservation_returns_404(client: AsyncClient) -> None:
    response = await client.delete(f"/api/v1/reservations/{uuid4()}", headers=USER)

    assert response.status_code == 404


async def test_reservation_of_another_user_returns_404(client: AsyncClient) -> None:
    created = (await client.post("/api/v1/reservations", headers=USER, json=BOOKING)).json()

    response = await client.get(
        f"/api/v1/reservations/{created['reservationUid']}",
        headers={"X-User-Name": "Someone Else"},
    )

    assert response.status_code == 404


async def test_health_is_up(client: AsyncClient) -> None:
    response = await client.get("/manage/health")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}
