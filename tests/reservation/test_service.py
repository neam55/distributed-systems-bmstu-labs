from datetime import date
from uuid import UUID, uuid4

import pytest

from common.errors import NotFoundError
from reservation.entities import Reservation, ReservationStatus
from reservation.service import ReservationService

from .conftest import ARARAT_FULL_ADDRESS, ARARAT_UID, TEST_USER

START = date(2021, 10, 8)
END = date(2021, 10, 11)


async def book(
    service: ReservationService,
    username: str = TEST_USER,
    hotel_uid: UUID = ARARAT_UID,
) -> Reservation:
    return await service.create_reservation(
        username=username,
        payment_uid=uuid4(),
        hotel_uid=hotel_uid,
        start_date=START,
        end_date=END,
    )


async def test_first_page_contains_all_three_hotels(service: ReservationService) -> None:
    page = await service.list_hotels(page=1, size=10)

    assert page.page == 1
    assert page.total_elements == 3
    assert page.page_size == 3
    assert page.items[0].hotel_uid == ARARAT_UID


async def test_page_size_never_exceeds_requested_size(service: ReservationService) -> None:
    page = await service.list_hotels(page=1, size=2)

    assert page.page_size == 2
    assert page.total_elements == 3


async def test_second_page_continues_after_first(service: ReservationService) -> None:
    first = await service.list_hotels(page=1, size=2)
    second = await service.list_hotels(page=2, size=2)

    assert second.page == 2
    assert second.page_size == 1
    assert {item.hotel_uid for item in first.items}.isdisjoint({item.hotel_uid for item in second.items})


async def test_page_beyond_last_is_empty_but_keeps_total(service: ReservationService) -> None:
    page = await service.list_hotels(page=5, size=10)

    assert page.items == []
    assert page.page_size == 0
    assert page.total_elements == 3


async def test_hotel_full_address_is_assembled(service: ReservationService) -> None:
    hotel = await service.get_hotel(ARARAT_UID)

    assert hotel.full_address == ARARAT_FULL_ADDRESS


async def test_unknown_hotel_raises(service: ReservationService) -> None:
    with pytest.raises(NotFoundError):
        await service.get_hotel(uuid4())


async def test_created_reservation_is_paid(service: ReservationService) -> None:
    reservation = await book(service)

    assert reservation.status == ReservationStatus.PAID
    assert reservation.hotel.hotel_uid == ARARAT_UID
    assert (reservation.start_date, reservation.end_date) == (START, END)


async def test_booking_unknown_hotel_raises(service: ReservationService) -> None:
    with pytest.raises(NotFoundError):
        await book(service, hotel_uid=uuid4())


async def test_reservation_of_another_user_is_not_found(service: ReservationService) -> None:
    reservation = await book(service, username="Someone Else")

    with pytest.raises(NotFoundError):
        await service.get_reservation(reservation.reservation_uid, TEST_USER)


async def test_list_returns_only_own_reservations(service: ReservationService) -> None:
    mine = await book(service)
    await book(service, username="Someone Else")

    reservations = await service.list_reservations(TEST_USER)

    assert [item.reservation_uid for item in reservations] == [mine.reservation_uid]


async def test_cancel_sets_canceled_status(service: ReservationService) -> None:
    reservation = await book(service)

    canceled = await service.cancel_reservation(reservation.reservation_uid, TEST_USER)

    assert canceled.status == ReservationStatus.CANCELED
    assert canceled.payment_uid == reservation.payment_uid


async def test_cancel_of_another_user_raises(service: ReservationService) -> None:
    reservation = await book(service, username="Someone Else")

    with pytest.raises(NotFoundError):
        await service.cancel_reservation(reservation.reservation_uid, TEST_USER)
