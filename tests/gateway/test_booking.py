"""Сценарии оркестрации Gateway."""

from datetime import date
from uuid import UUID, uuid4

import pytest

from common.errors import NotFoundError, UpstreamError, ValidationError
from gateway.schemas import CreateReservationRequest
from gateway.service import BookingService, apply_discount
from tests.gateway.fakes import (
    FakeLoyaltyServiceClient,
    FakePaymentServiceClient,
    FakeReservationServiceClient,
)

from .conftest import ARARAT_FULL_ADDRESS, ARARAT_UID, EXPECTED_PRICE, TEST_USER

REQUEST = CreateReservationRequest(
    hotel_uid=ARARAT_UID,
    start_date=date(2021, 10, 8),
    end_date=date(2021, 10, 11),
)


@pytest.mark.parametrize(
    ("price", "discount", "expected"),
    [(30000, 10, 27000), (30000, 7, 27900), (30000, 5, 28500), (30000, 0, 30000)],
)
def test_discount_is_applied_as_integer_percent(price: int, discount: int, expected: int) -> None:
    assert apply_discount(price, discount) == expected


async def test_booking_charges_nights_minus_loyalty_discount(service: BookingService) -> None:
    result = await service.book(TEST_USER, REQUEST)

    assert result.hotel_uid == ARARAT_UID
    assert result.start_date == date(2021, 10, 8)
    assert result.end_date == date(2021, 10, 11)
    assert result.discount == 10
    assert result.status == "PAID"
    assert result.payment.status == "PAID"
    assert result.payment.price == EXPECTED_PRICE


async def test_booking_calls_services_in_contract_order(service: BookingService, calls: list[str]) -> None:
    await service.book(TEST_USER, REQUEST)

    assert calls == [
        "reservation.get_hotel",
        "loyalty.get",
        f"payment.create({EXPECTED_PRICE})",
        "reservation.create_reservation",
        "loyalty.change_count(+1)",
    ]


async def test_booking_increments_loyalty_counter(
    service: BookingService, loyalty: FakeLoyaltyServiceClient
) -> None:
    await service.book(TEST_USER, REQUEST)

    assert loyalty.reservation_count == 26


async def test_booking_unknown_hotel_raises_not_found(service: BookingService, calls: list[str]) -> None:
    request = REQUEST.model_copy(update={"hotel_uid": uuid4()})

    with pytest.raises(NotFoundError):
        await service.book(TEST_USER, request)

    # Ни оплата, ни счётчик лояльности не должны быть затронуты.
    assert calls == ["reservation.get_hotel"]


@pytest.mark.parametrize("end_date", [date(2021, 10, 8), date(2021, 10, 7)])
async def test_end_date_must_be_after_start_date(
    service: BookingService, calls: list[str], end_date: date
) -> None:
    request = REQUEST.model_copy(update={"end_date": end_date})

    with pytest.raises(ValidationError) as exc_info:
        await service.book(TEST_USER, request)

    assert "endDate" in exc_info.value.errors
    assert calls == []


async def test_bronze_user_gets_five_percent(
    service: BookingService, loyalty: FakeLoyaltyServiceClient
) -> None:
    loyalty.reservation_count = 0

    result = await service.book(TEST_USER, REQUEST)

    assert result.discount == 5
    assert result.payment.price == 28500


async def test_cancel_cancels_reservation_payment_and_counter(
    service: BookingService,
    calls: list[str],
    payments: FakePaymentServiceClient,
    reservations: FakeReservationServiceClient,
    loyalty: FakeLoyaltyServiceClient,
) -> None:
    booked = await service.book(TEST_USER, REQUEST)
    calls.clear()

    await service.cancel(booked.reservation_uid, TEST_USER)

    assert calls == [
        "reservation.get_reservation",
        "payment.cancel",
        "reservation.cancel_reservation",
        "loyalty.change_count(-1)",
    ]
    assert reservations.reservations[booked.reservation_uid].status == "CANCELED"
    assert [payment.status for payment in payments.payments.values()] == ["CANCELED"]
    assert loyalty.reservation_count == 25


async def test_cancel_of_another_user_raises_not_found(service: BookingService) -> None:
    booked = await service.book(TEST_USER, REQUEST)

    with pytest.raises(NotFoundError):
        await service.cancel(booked.reservation_uid, "Someone Else")


async def test_cancel_unknown_reservation_raises_not_found(service: BookingService) -> None:
    with pytest.raises(NotFoundError):
        await service.cancel(uuid4(), TEST_USER)


async def test_cancel_retry_completes_after_payment_failure(
    service: BookingService,
    payments: FakePaymentServiceClient,
    loyalty: FakeLoyaltyServiceClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    booked = await service.book(TEST_USER, REQUEST)
    original = payments.cancel

    async def unavailable(payment_uid: object) -> None:
        raise UpstreamError("Payment", "temporarily unavailable")

    monkeypatch.setattr(payments, "cancel", unavailable)
    with pytest.raises(UpstreamError):
        await service.cancel(booked.reservation_uid, TEST_USER)
    monkeypatch.setattr(payments, "cancel", original)

    await service.cancel(booked.reservation_uid, TEST_USER)

    assert loyalty.reservation_count == 25
    assert [payment.status for payment in payments.payments.values()] == ["CANCELED"]


async def test_cancel_retry_after_lost_loyalty_response_does_not_decrement_twice(
    service: BookingService,
    loyalty: FakeLoyaltyServiceClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    booked = await service.book(TEST_USER, REQUEST)
    original = loyalty.change_count

    async def lost_response(username: str, delta: int, operation_uid: UUID | None = None) -> None:
        await original(username, delta, operation_uid)
        raise UpstreamError("Loyalty", "response lost")

    monkeypatch.setattr(loyalty, "change_count", lost_response)
    await service.cancel(booked.reservation_uid, TEST_USER)
    assert service.recovery.pending
    monkeypatch.setattr(loyalty, "change_count", original)

    await service.cancel(booked.reservation_uid, TEST_USER)

    assert loyalty.reservation_count == 25


async def test_reservation_list_joins_payment_data(service: BookingService) -> None:
    booked = await service.book(TEST_USER, REQUEST)

    reservations = await service.list_reservations(TEST_USER)

    assert len(reservations) == 1
    item = reservations[0]
    assert item.reservation_uid == booked.reservation_uid
    assert item.hotel.full_address == ARARAT_FULL_ADDRESS
    assert item.payment is not None
    assert item.payment.price == EXPECTED_PRICE


async def test_list_returns_only_own_reservations(service: BookingService) -> None:
    await service.book(TEST_USER, REQUEST)
    await service.book("Someone Else", REQUEST)

    assert len(await service.list_reservations(TEST_USER)) == 1


async def test_user_info_contains_reservations_and_loyalty(service: BookingService) -> None:
    await service.book(TEST_USER, REQUEST)

    info = await service.get_user_info(TEST_USER)

    assert len(info.reservations) == 1
    assert info.loyalty.status == "GOLD"
    assert info.loyalty.discount == 10
    assert info.loyalty.reservation_count == 26


async def test_single_reservation_is_fetched_with_payment(service: BookingService) -> None:
    booked = await service.book(TEST_USER, REQUEST)

    item = await service.get_reservation(booked.reservation_uid, TEST_USER)

    assert item.payment is not None
    assert item.payment.price == EXPECTED_PRICE


async def test_single_reservation_of_another_user_raises(service: BookingService) -> None:
    booked = await service.book(TEST_USER, REQUEST)

    with pytest.raises(NotFoundError):
        await service.get_reservation(booked.reservation_uid, "Someone Else")
