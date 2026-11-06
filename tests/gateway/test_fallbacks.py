from uuid import uuid4

import pytest

from common.errors import NotFoundError, UpstreamError
from gateway.service import BookingService
from tests.gateway.conftest import TEST_USER
from tests.gateway.fakes import (
    FakeLoyaltyServiceClient,
    FakePaymentServiceClient,
    FakeReservationServiceClient,
)
from tests.gateway.test_booking import REQUEST


async def test_me_preserves_reservations_when_payment_and_loyalty_fail(
    service: BookingService,
    payments: FakePaymentServiceClient,
    loyalty: FakeLoyaltyServiceClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    booked = await service.book(TEST_USER, REQUEST)

    async def unavailable(*args: object) -> None:
        raise UpstreamError("test", "down")

    monkeypatch.setattr(payments, "list_by_uids", unavailable)
    monkeypatch.setattr(loyalty, "get", unavailable)
    data = (await service.get_user_info(TEST_USER)).model_dump(by_alias=True)
    assert data["loyalty"] == {}
    assert data["reservations"][0]["reservationUid"] == booked.reservation_uid
    assert data["reservations"][0]["payment"] == {}


async def test_critical_source_failure_propagates(
    service: BookingService,
    reservations: FakeReservationServiceClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def unavailable(*args: object) -> None:
        raise UpstreamError("Reservation", "down")

    monkeypatch.setattr(reservations, "list_reservations", unavailable)
    with pytest.raises(UpstreamError):
        await service.get_user_info(TEST_USER)


async def test_booking_rolls_back_committed_loyalty_when_response_lost(
    service: BookingService,
    payments: FakePaymentServiceClient,
    reservations: FakeReservationServiceClient,
    loyalty: FakeLoyaltyServiceClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = loyalty.change_count

    async def lost_response(*args: object, **kwargs: object) -> None:
        await original(*args, **kwargs)
        raise UpstreamError("Loyalty", "response lost")

    monkeypatch.setattr(loyalty, "change_count", lost_response)
    with pytest.raises(UpstreamError):
        await service.book(TEST_USER, REQUEST)
    assert loyalty.reservation_count == 25
    assert all(item.status == "CANCELED" for item in payments.payments.values())
    assert all(item.status == "CANCELED" for item in reservations.reservations.values())
    assert await service.list_reservations(TEST_USER) == []
    uid = next(iter(reservations.reservations))
    with pytest.raises(NotFoundError):
        await service.cancel(uid, TEST_USER)
    assert loyalty.reservation_count == 25


async def test_failed_payment_cancel_leaves_reservation_paid(
    service: BookingService,
    reservations: FakeReservationServiceClient,
    payments: FakePaymentServiceClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    booked = await service.book(TEST_USER, REQUEST)

    async def unavailable(*args: object) -> None:
        raise UpstreamError("Payment", "down")

    monkeypatch.setattr(payments, "cancel", unavailable)
    with pytest.raises(UpstreamError):
        await service.cancel(booked.reservation_uid, TEST_USER)
    assert reservations.reservations[booked.reservation_uid].status == "PAID"


async def test_empty_reservations_skip_payment_lookup(
    service: BookingService,
    calls: list[str],
) -> None:
    assert await service.list_reservations(str(uuid4())) == []
    assert calls == ["reservation.list_reservations"]
