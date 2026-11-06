from httpx import ASGITransport, AsyncClient

from gateway.main import create_app


async def test_each_lifespan_gets_fresh_clients_and_worker() -> None:
    app = create_app()
    async with app.router.lifespan_context(app):
        first_client = app.state.payment_http
        first_queue = app.state.recovery
        assert first_queue._worker is not None
    assert first_client._client.is_closed
    assert first_queue._worker is None
    async with app.router.lifespan_context(app):
        assert app.state.payment_http is not first_client
        assert app.state.recovery is not first_queue
        assert not app.state.payment_http._client.is_closed


async def test_gateway_health_does_not_call_dependencies() -> None:
    app = create_app()
    # No lifespan means upstream clients are absent entirely.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/manage/health")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}
