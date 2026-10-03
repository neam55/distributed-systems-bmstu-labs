"""HTTP-клиент для межсервисного взаимодействия.

Используется только Gateway: горизонтальные вызовы между остальными сервисами запрещены.
"""

from typing import Any

import httpx

from common.errors import UpstreamError

USER_HEADER = "X-User-Name"


class ServiceClient:
    """Тонкая обёртка над httpx.AsyncClient с базовым URL одного сервиса."""

    def __init__(self, name: str, base_url: str, *, timeout: float = 10.0) -> None:
        self.name = name
        self._client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout)

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
        try:
            response = await self._client.request(method, path, params=params, json=json, headers=headers)
        except httpx.HTTPError as exc:
            raise UpstreamError(self.name, str(exc)) from exc

        if not_found_ok and response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise UpstreamError(self.name, f"{method} {path} responded {response.status_code}")
        return response
