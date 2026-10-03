from uuid import uuid4

import pytest

from common.errors import NotFoundError
from payment.entities import PaymentStatus
from payment.service import PaymentService


async def test_created_payment_is_paid_with_unique_uid(service: PaymentService) -> None:
    first = await service.create(27000)
    second = await service.create(27000)

    assert first.status == PaymentStatus.PAID
    assert first.price == 27000
    assert first.payment_uid != second.payment_uid


async def test_payment_can_be_fetched_by_uid(service: PaymentService) -> None:
    created = await service.create(27000)

    assert await service.get(created.payment_uid) == created


async def test_missing_payment_raises(service: PaymentService) -> None:
    with pytest.raises(NotFoundError):
        await service.get(uuid4())


async def test_cancel_switches_status(service: PaymentService) -> None:
    created = await service.create(27000)

    canceled = await service.cancel(created.payment_uid)

    assert canceled.status == PaymentStatus.CANCELED
    assert canceled.price == 27000
    assert (await service.get(created.payment_uid)).status == PaymentStatus.CANCELED


async def test_cancel_missing_payment_raises(service: PaymentService) -> None:
    with pytest.raises(NotFoundError):
        await service.cancel(uuid4())


async def test_batch_lookup_skips_unknown_uids(service: PaymentService) -> None:
    first = await service.create(100)
    second = await service.create(200)

    found = await service.list_by_uids([first.payment_uid, uuid4(), second.payment_uid])

    assert [item.price for item in found] == [100, 200]


async def test_batch_lookup_of_empty_list(service: PaymentService) -> None:
    assert await service.list_by_uids([]) == []
