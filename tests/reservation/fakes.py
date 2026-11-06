from dataclasses import replace
from datetime import date
from uuid import UUID

from fastapi import HTTPException

from reservation.entities import Hotel, Reservation, ReservationStatus
from reservation.repository import ReservationRepository


class InMemoryReservationRepository(ReservationRepository):
    """Хранилище отелей и бронирований в памяти."""

    def __init__(self, hotels: list[Hotel]) -> None:
        self._hotels: list[Hotel] = [replace(hotel, id=index) for index, hotel in enumerate(hotels, 1)]
        self._reservations: dict[UUID, Reservation] = {}
        self._next_id = 1
        self._canceled: dict[UUID, str] = {}

    async def list_hotels(self, *, offset: int, limit: int) -> list[Hotel]:
        return [replace(hotel) for hotel in self._hotels[offset : offset + limit]]

    async def count_hotels(self) -> int:
        return len(self._hotels)

    async def get_hotel(self, hotel_uid: UUID) -> Hotel | None:
        for hotel in self._hotels:
            if hotel.hotel_uid == hotel_uid:
                return replace(hotel)
        return None

    async def list_reservations(self, username: str) -> list[Reservation]:
        ordered = sorted(self._reservations.values(), key=lambda value: value.id or 0)
        return [
            replace(item)
            for item in ordered
            if item.username == username and item.reservation_uid not in self._canceled
        ]

    async def get_reservation(self, reservation_uid: UUID, username: str) -> Reservation | None:
        found = self._reservations.get(reservation_uid)
        if found is None or found.username != username or reservation_uid in self._canceled:
            return None
        return replace(found)

    async def add_reservation(
        self,
        *,
        reservation_uid: UUID,
        username: str,
        payment_uid: UUID,
        hotel_uid: UUID,
        start_date: date,
        end_date: date,
    ) -> Reservation | None:
        existing = self._reservations.get(reservation_uid)
        if existing is not None:
            if (
                existing.username,
                existing.payment_uid,
                existing.hotel.hotel_uid,
                existing.start_date,
                existing.end_date,
            ) != (username, payment_uid, hotel_uid, start_date, end_date):
                raise HTTPException(status_code=409, detail="Reservation UID payload conflict")
            return replace(existing)
        if reservation_uid in self._canceled and self._canceled[reservation_uid] != username:
            raise HTTPException(status_code=409, detail="Reservation UID owner conflict")
        hotel = await self.get_hotel(hotel_uid)
        if hotel is None:
            return None
        stored = Reservation(
            id=self._next_id,
            reservation_uid=reservation_uid,
            username=username,
            payment_uid=payment_uid,
            hotel=hotel,
            status=(
                ReservationStatus.CANCELED if reservation_uid in self._canceled else ReservationStatus.PAID
            ),
            start_date=start_date,
            end_date=end_date,
        )
        self._next_id += 1
        self._reservations[reservation_uid] = stored
        return replace(stored)

    async def set_status(
        self, reservation_uid: UUID, username: str, status: ReservationStatus
    ) -> Reservation | None:
        found = self._reservations.get(reservation_uid)
        if found is None or found.username != username or reservation_uid in self._canceled:
            return None
        updated = replace(found, status=status)
        self._reservations[reservation_uid] = updated
        return replace(updated)

    async def compensate(self, reservation_uid: UUID, username: str) -> None:
        existing = self._reservations.get(reservation_uid)
        if (existing is not None and existing.username != username) or (
            reservation_uid in self._canceled and self._canceled[reservation_uid] != username
        ):
            raise HTTPException(status_code=404, detail="Reservation not found")
        self._canceled[reservation_uid] = username
        if existing is not None:
            self._reservations[reservation_uid] = replace(existing, status=ReservationStatus.CANCELED)
