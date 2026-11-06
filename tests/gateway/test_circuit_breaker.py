import asyncio

import httpx
import pytest

from common.errors import UpstreamError
from common.http import ServiceClient
from gateway.circuit_breaker import CircuitBreaker


async def test_fourth_request_skips_transport_after_three_failures() -> None:
    calls = 0

    def fail(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    clock = [0.0]
    breaker = CircuitBreaker("Payment", clock=lambda: clock[0])
    client = ServiceClient("Payment", "http://test", read_guard=breaker, transport=httpx.MockTransport(fail))
    for _ in range(4):
        with pytest.raises(UpstreamError):
            await client.send("GET", "/")
    assert calls == 3
    clock[0] = 5
    with pytest.raises(UpstreamError):
        await client.send("GET", "/")
    assert calls == 4
    assert breaker.state == "OPEN"
    await client.aclose()


async def test_only_one_half_open_probe_and_cancel_releases_slot() -> None:
    clock = [0.0]
    breaker = CircuitBreaker("Payment", threshold=1, clock=lambda: clock[0])

    async def fail() -> httpx.Response:
        raise UpstreamError("Payment", "down")

    with pytest.raises(UpstreamError):
        await breaker.call(fail)
    clock[0] = 5
    started = asyncio.Event()

    async def probe() -> httpx.Response:
        started.set()
        await asyncio.Event().wait()
        return httpx.Response(200)

    task = asyncio.create_task(breaker.call(probe))
    await started.wait()
    with pytest.raises(UpstreamError):
        await breaker.call(probe)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert breaker.state == "OPEN"


async def test_404_is_not_failure_and_writes_bypass_open_breaker() -> None:
    breaker = CircuitBreaker("Payment", threshold=1)
    statuses = iter([404, 500, 200])
    client = ServiceClient(
        "Payment",
        "http://test",
        read_guard=breaker,
        transport=httpx.MockTransport(lambda _: httpx.Response(next(statuses))),
    )
    assert await client.send("GET", "/", not_found_ok=True) is None
    assert breaker.failures == 0
    with pytest.raises(UpstreamError):
        await client.send("GET", "/")
    response = await client.send("POST", "/")
    assert response is not None and response.status_code == 200
    await client.aclose()


async def test_success_resets_failures_and_successful_probe_recovers() -> None:
    clock = [0.0]
    breaker = CircuitBreaker("Payment", threshold=2, clock=lambda: clock[0])

    async def fail() -> httpx.Response:
        raise UpstreamError("Payment", "down")

    async def success() -> httpx.Response:
        return httpx.Response(200)

    with pytest.raises(UpstreamError):
        await breaker.call(fail)
    await breaker.call(success)
    assert breaker.failures == 0
    for _ in range(2):
        with pytest.raises(UpstreamError):
            await breaker.call(fail)
    assert breaker.state == "OPEN"
    clock[0] = 5
    await breaker.call(success)
    assert breaker.state == "CLOSED"
    assert breaker.failures == 0


async def test_stale_success_does_not_close_new_generation() -> None:
    breaker = CircuitBreaker("Payment", threshold=1)
    started, release = asyncio.Event(), asyncio.Event()

    async def slow_success() -> httpx.Response:
        started.set()
        await release.wait()
        return httpx.Response(200)

    async def fail() -> httpx.Response:
        raise UpstreamError("Payment", "down")

    task = asyncio.create_task(breaker.call(slow_success))
    await started.wait()
    with pytest.raises(UpstreamError):
        await breaker.call(fail)
    release.set()
    await task
    assert breaker.state == "OPEN"
