from httpx import AsyncClient


async def test_create_returns_201_with_location_and_empty_body(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/persons",
        json={"name": "Ivan", "age": 31, "address": "Moscow", "work": "BMSTU"},
    )

    assert response.status_code == 201
    assert response.content == b""
    location = response.headers["Location"]
    person_id = int(location.rsplit("/", 1)[-1])
    assert location == f"/api/v1/persons/{person_id}"

    created = await client.get(location)
    assert created.status_code == 200
    assert created.json()["id"] == person_id


async def test_invalid_payload_returns_400_validation_error(client: AsyncClient) -> None:
    response = await client.post("/api/v1/persons", json={"age": 10})

    assert response.status_code == 400
    body = response.json()
    assert body["message"]
    assert "name" in body["errors"]


async def test_get_missing_person_returns_404_error_response(client: AsyncClient) -> None:
    response = await client.get("/api/v1/persons/999999")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"message": "Person with id 999999 not found"}


async def test_patch_updates_only_provided_fields(client: AsyncClient) -> None:
    location = (
        await client.post(
            "/api/v1/persons",
            json={"name": "Ivan", "age": 31, "address": "Moscow", "work": "BMSTU"},
        )
    ).headers["Location"]

    response = await client.patch(location, json={"name": "Petr", "address": "Tver"})

    assert response.status_code == 200
    assert response.json() == {
        "id": int(location.rsplit("/", 1)[-1]),
        "name": "Petr",
        "age": 31,
        "address": "Tver",
        "work": "BMSTU",
    }


async def test_delete_returns_204_then_404(client: AsyncClient) -> None:
    location = (await client.post("/api/v1/persons", json={"name": "Ivan"})).headers["Location"]

    deleted = await client.delete(location)
    assert deleted.status_code == 204
    assert deleted.content == b""

    assert (await client.delete(location)).status_code == 404


async def test_list_persons_returns_array(client: AsyncClient) -> None:
    await client.post("/api/v1/persons", json={"name": "Ivan"})
    await client.post("/api/v1/persons", json={"name": "Petr"})

    response = await client.get("/api/v1/persons")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert [item["name"] for item in body] == ["Ivan", "Petr"]
