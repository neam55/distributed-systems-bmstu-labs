from dataclasses import replace
from datetime import date
from uuid import UUID

from reservation.entities import Hotel, Reservation, ReservationStatus
from reservation.repository import ReservationRepository


class InMemoryReservationRepository(ReservationRepository):
    """Хранилище отелей и бронирований в памяти."""

    def __init__(self, hotels: list[Hotel]) -> None:
        self._hotels: list[Hotel] = [replace(hotel, id=index) for index, hotel in enumerate(hotels, 1)]
        self._reservations: dict[UUID, Reservation] = {}
        self._next_id = 1

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
        return [replace(item) for item in ordered if item.username == username]

    async def get_reservation(self, reservation_uid: UUID, username: str) -> Reservation | None:
        found = self._reservations.get(reservation_uid)
        if found is None or found.username != username:
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
        hotel = await self.get_hotel(hotel_uid)
        if hotel is None:
            return None
        stored = Reservation(
            id=self._next_id,
            reservation_uid=reservation_uid,
            username=username,
            payment_uid=payment_uid,
            hotel=hotel,
            status=ReservationStatus.PAID,
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
        if found is None or found.username != username:
            return None
        updated = replace(found, status=status)
        self._reservations[reservation_uid] = updated
        return replace(updated)
