import httpx
import pytest

from common.errors import UpstreamError
from common.http import ServiceClient


@pytest.mark.parametrize("error_type", [httpx.ConnectError, httpx.ReadTimeout])
async def test_transport_errors_are_retryable(error_type: type[httpx.TransportError]) -> None:
    def transport(request: httpx.Request) -> httpx.Response:
        raise error_type("broken", request=request)

    client = ServiceClient("Loyalty", "http://test", transport=httpx.MockTransport(transport))
    with pytest.raises(UpstreamError) as caught:
        await client.send("GET", "/")
    assert caught.value.retryable
    assert str(caught.value) == "Loyalty Service unavailable"
    await client.aclose()


@pytest.mark.parametrize(("status", "retryable"), [(400, False), (409, False), (500, True), (503, True)])
async def test_http_failure_classification_and_no_automatic_write_retry(status: int, retryable: bool) -> None:
    calls = 0

    def transport(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status)

    client = ServiceClient("Payment", "http://test", transport=httpx.MockTransport(transport))
    with pytest.raises(UpstreamError) as caught:
        await client.send("POST", "/")
    assert caught.value.retryable is retryable
    assert caught.value.status_code == status
    assert calls == 1
    await client.aclose()
