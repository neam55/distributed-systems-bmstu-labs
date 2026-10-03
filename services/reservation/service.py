"""Бизнес-логика Reservation Service."""

from datetime import date
from uuid import UUID, uuid4

from common.errors import NotFoundError
from reservation.entities import Hotel, HotelPage, Reservation, ReservationStatus
from reservation.repository import ReservationRepository


class ReservationService:
    def __init__(self, repository: ReservationRepository) -> None:
        self._repository = repository

    async def list_hotels(self, page: int, size: int) -> HotelPage:
        """Страница справочника. Нумерация страниц с единицы."""
        items = await self._repository.list_hotels(offset=(page - 1) * size, limit=size)
        total = await self._repository.count_hotels()
        return HotelPage(page=page, total_elements=total, items=items)

    async def get_hotel(self, hotel_uid: UUID) -> Hotel:
        hotel = await self._repository.get_hotel(hotel_uid)
        if hotel is None:
            raise NotFoundError(f"Hotel with uid {hotel_uid} not found")
        return hotel

    async def list_reservations(self, username: str) -> list[Reservation]:
        return await self._repository.list_reservations(username)

    async def get_reservation(self, reservation_uid: UUID, username: str) -> Reservation:
        """Бронирование пользователя.

        Чужое бронирование неотличимо от отсутствующего: оба дают 404, чтобы не
        раскрывать существование брони другого пользователя.
        """
        reservation = await self._repository.get_reservation(reservation_uid, username)
        if reservation is None:
            raise NotFoundError(f"Reservation with uid {reservation_uid} not found")
        return reservation

    async def create_reservation(
        self,
        *,
        username: str,
        payment_uid: UUID,
        hotel_uid: UUID,
        start_date: date,
        end_date: date,
    ) -> Reservation:
        """Создать оплаченное бронирование. Мест в отеле считаем бесконечно много."""
        reservation = await self._repository.add_reservation(
            reservation_uid=uuid4(),
            username=username,
            payment_uid=payment_uid,
            hotel_uid=hotel_uid,
            start_date=start_date,
            end_date=end_date,
        )
        if reservation is None:
            raise NotFoundError(f"Hotel with uid {hotel_uid} not found")
        return reservation

    async def cancel_reservation(self, reservation_uid: UUID, username: str) -> Reservation:
        canceled = await self._repository.set_status(
            reservation_uid, username, ReservationStatus.CANCELED
        )
        if canceled is None:
            raise NotFoundError(f"Reservation with uid {reservation_uid} not found")
        return canceled
