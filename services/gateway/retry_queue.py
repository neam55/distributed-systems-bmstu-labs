"""Process-local recovery queue; delayed jobs do not block ready jobs."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from common.errors import UpstreamError

logger = logging.getLogger(__name__)


class RecoveryKind(StrEnum):
    CANCEL_PAYMENT = "cancel_payment"
    CANCEL_RESERVATION = "cancel_reservation"
    REVERSE_BOOKING_LOYALTY = "reverse_booking_loyalty"
    COMPLETE_CANCELLATION = "complete_cancellation"


@dataclass(frozen=True)
class RetryJob:
    kind: RecoveryKind
    username: str
    operation_uid: UUID
    payment_uid: UUID | None = None
    reservation_uid: UUID | None = None


class RetryQueue:
    def __init__(
        self,
        execute: Callable[[RetryJob], Awaitable[None]],
        *,
        retry_interval: float = 10,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.execute = execute
        self.retry_interval = retry_interval
        self.sleep = sleep
        self.queue: asyncio.Queue[RetryJob] = asyncio.Queue()
        self.pending: set[tuple[RecoveryKind, str, UUID]] = set()
        self._initial_delays: set[tuple[RecoveryKind, str, UUID]] = set()
        self._worker: asyncio.Task[None] | None = None
        self._delayed: set[asyncio.Task[None]] = set()

    async def enqueue(self, job: RetryJob, *, delay: bool = False) -> None:
        key = (job.kind, job.username, job.operation_uid)
        if key not in self.pending:
            self.pending.add(key)
            if delay:
                self._initial_delays.add(key)
            self.queue.put_nowait(job)

    def start(self) -> None:
        if self._worker is None:
            self._worker = asyncio.create_task(self._run())

    async def stop(self) -> None:
        tasks = [*self._delayed]
        if self._worker is not None:
            tasks.append(self._worker)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._worker = None
        self._delayed.clear()

    async def _later(self, job: RetryJob) -> None:
        await self.sleep(self.retry_interval)
        self.queue.put_nowait(job)

    async def _run(self) -> None:
        while True:
            job = await self.queue.get()
            key = (job.kind, job.username, job.operation_uid)
            try:
                if key in self._initial_delays:
                    self._initial_delays.remove(key)
                    task = asyncio.create_task(self._later(job))
                    self._delayed.add(task)
                    task.add_done_callback(self._delayed.discard)
                    continue
                await self.execute(job)
            except UpstreamError as exc:
                if exc.retryable:
                    logger.warning("Recovery retry: %s %s (%s)", job.kind, job.operation_uid, exc.detail)
                    task = asyncio.create_task(self._later(job))
                    self._delayed.add(task)
                    task.add_done_callback(self._delayed.discard)
                else:
                    logger.exception("Permanent recovery failure: %s", job)
                    self.pending.discard(key)
            except Exception:
                logger.exception("Unexpected recovery failure: %s", job)
                task = asyncio.create_task(self._later(job))
                self._delayed.add(task)
                task.add_done_callback(self._delayed.discard)
            else:
                self.pending.discard(key)
            finally:
                self.queue.task_done()
