"""Concurrency-safe, process-local circuit breaker for upstream reads."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable

import httpx

from common.errors import UpstreamError

logger = logging.getLogger(__name__)


class CircuitBreaker:
    def __init__(
        self,
        service: str,
        threshold: int = 3,
        recovery_timeout: float = 5.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if threshold <= 0 or recovery_timeout <= 0:
            raise ValueError("Circuit breaker settings must be positive")
        self.service = service
        self.threshold = threshold
        self.recovery_timeout = recovery_timeout
        self.clock = clock
        self.state = "CLOSED"
        self.failures = 0
        self._opened_at = 0.0
        self._generation = 0
        self._lock = asyncio.Lock()

    def _transition(self, state: str) -> None:
        logger.info("Circuit breaker %s: %s -> %s", self.service, self.state, state)
        self.state = state
        self._generation += 1

    async def call(self, request: Callable[[], Awaitable[httpx.Response]]) -> httpx.Response:
        async with self._lock:
            if self.state == "OPEN" and self.clock() - self._opened_at >= self.recovery_timeout:
                self._transition("HALF_OPEN")
            elif self.state != "CLOSED":
                raise UpstreamError(self.service, "Circuit is open")
            generation = self._generation
            probe = self.state == "HALF_OPEN"
        try:
            response = await request()
        except BaseException as exc:
            async with self._lock:
                if generation == self._generation:
                    if isinstance(exc, UpstreamError) and exc.retryable:
                        self.failures += 1
                        if probe or self.failures >= self.threshold:
                            self._opened_at = self.clock()
                            self._transition("OPEN")
                    elif probe:
                        if isinstance(exc, asyncio.CancelledError):
                            self._opened_at = self.clock()
                            self._transition("OPEN")
                        else:
                            self.failures = 0
                            self._transition("CLOSED")
            raise
        async with self._lock:
            if generation == self._generation:
                self.failures = 0
                if probe:
                    self._transition("CLOSED")
        return response
