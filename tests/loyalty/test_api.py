from uuid import uuid4

from httpx import AsyncClient

from .conftest import TEST_USER


async def test_get_loyalty_returns_camel_case_contract(client: AsyncClient) -> None:
    response = await client.get("/api/v1/loyalty", headers={"X-User-Name": TEST_USER})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "GOLD", "discount": 10, "reservationCount": 25}


async def test_patch_loyalty_changes_counter(client: AsyncClient) -> None:
    response = await client.patch(
        "/api/v1/loyalty", headers={"X-User-Name": TEST_USER}, json={"delta": 1}
    )

    assert response.status_code == 200
    assert response.json()["reservationCount"] == 26


async def test_missing_user_header_is_400(client: AsyncClient) -> None:
    response = await client.get("/api/v1/loyalty")

    assert response.status_code == 400
    body = response.json()
    assert body["message"]
    assert [error["field"] for error in body["errors"]] == ["X-User-Name"]


async def test_health_is_up(client: AsyncClient) -> None:
    response = await client.get("/manage/health")

    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


async def test_repeated_operation_changes_counter_once(client: AsyncClient) -> None:
    payload = {"delta": -1, "operationUid": str(uuid4())}
    for _ in range(2):
        response = await client.patch(
            "/api/v1/loyalty", headers={"X-User-Name": TEST_USER}, json=payload
        )
        assert response.status_code == 200
        assert response.json()["reservationCount"] == 24


async def test_different_operations_both_change_counter(client: AsyncClient) -> None:
    for expected_count in (24, 23):
        response = await client.patch(
            "/api/v1/loyalty",
            headers={"X-User-Name": TEST_USER},
            json={"delta": -1, "operationUid": str(uuid4())},
        )
        assert response.status_code == 200
        assert response.json()["reservationCount"] == expected_count
