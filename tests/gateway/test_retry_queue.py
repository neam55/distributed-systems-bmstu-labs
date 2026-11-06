import asyncio
from uuid import uuid4

from common.errors import UpstreamError
from gateway.retry_queue import RecoveryKind, RetryJob, RetryQueue


async def test_deduplicates_pending_and_retries_until_success() -> None:
    calls = 0
    waiting = asyncio.Event()
    release = asyncio.Event()
    done = asyncio.Event()

    async def execute(job: RetryJob) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise UpstreamError("Loyalty", "down")
        done.set()

    async def sleep(delay: float) -> None:
        assert delay == 10
        waiting.set()
        await release.wait()

    queue = RetryQueue(execute, sleep=sleep)
    job = RetryJob(RecoveryKind.COMPLETE_CANCELLATION, "user", uuid4())
    await queue.enqueue(job)
    await queue.enqueue(job)
    queue.start()
    await asyncio.wait_for(waiting.wait(), 1)
    assert calls == 1
    assert len(queue.pending) == 1
    release.set()
    await asyncio.wait_for(done.wait(), 1)
    await queue.queue.join()
    assert not queue.pending
    await queue.stop()


async def test_live_failure_waits_ten_seconds_before_first_retry() -> None:
    waiting, release, done = asyncio.Event(), asyncio.Event(), asyncio.Event()

    async def execute(job: RetryJob) -> None:
        done.set()

    async def sleep(delay: float) -> None:
        assert delay == 10
        waiting.set()
        await release.wait()

    queue = RetryQueue(execute, sleep=sleep)
    await queue.enqueue(RetryJob(RecoveryKind.COMPLETE_CANCELLATION, "user", uuid4()), delay=True)
    queue.start()
    await asyncio.wait_for(waiting.wait(), 1)
    assert not done.is_set()
    release.set()
    await asyncio.wait_for(done.wait(), 1)
    await queue.stop()
