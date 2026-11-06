"""HTTP-клиент для межсервисного взаимодействия.

Используется только Gateway: горизонтальные вызовы между остальными сервисами запрещены.
"""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol

import httpx

from common.errors import UpstreamError

USER_HEADER = "X-User-Name"


class ReadGuard(Protocol):
    async def call(self, request: Callable[[], Awaitable[httpx.Response]]) -> httpx.Response: ...


class ServiceClient:
    """Тонкая обёртка над httpx.AsyncClient с базовым URL одного сервиса."""

    def __init__(
        self,
        name: str,
        base_url: str,
        *,
        timeout: float = 2.0,
        read_guard: ReadGuard | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.name = name
        self._guard = read_guard
        self._client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout, transport=transport)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def send(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        username: str | None = None,
        not_found_ok: bool = False,
    ) -> httpx.Response | None:
        """Выполняет запрос к сервису.

        Любая сетевая ошибка или ответ 4xx/5xx превращается в UpstreamError (-> 503),
        кроме 404 при not_found_ok=True: тогда возвращается None, и вызывающий код
        сам решает, что это значит.
        """
        headers = {USER_HEADER: username} if username is not None else None

        async def request() -> httpx.Response:
            try:
                result = await self._client.request(method, path, params=params, json=json, headers=headers)
            except httpx.HTTPError as exc:
                raise UpstreamError(self.name, str(exc)) from exc
            if result.status_code >= 500:
                raise UpstreamError(self.name, f"HTTP {result.status_code}", status_code=result.status_code)
            return result

        response = (
            await self._guard.call(request) if self._guard and method.upper() == "GET" else await request()
        )

        if not_found_ok and response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise UpstreamError(
                self.name,
                f"{method} {path} responded {response.status_code}",
                status_code=response.status_code,
                retryable=False,
            )
        return response
