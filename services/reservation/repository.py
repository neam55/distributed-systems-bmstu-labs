"""Хранилище отелей и бронирований."""

from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from reservation.entities import Hotel, Reservation, ReservationStatus
from reservation.models import HotelORM, ReservationORM, to_timestamp


class ReservationRepository(ABC):
    @abstractmethod
    async def list_hotels(self, *, offset: int, limit: int) -> list[Hotel]:
        """Страница справочника отелей."""

    @abstractmethod
    async def count_hotels(self) -> int:
        """Общее количество отелей."""

    @abstractmethod
    async def get_hotel(self, hotel_uid: UUID) -> Hotel | None:
        """Отель по его uid или None."""

    @abstractmethod
    async def list_reservations(self, username: str) -> list[Reservation]:
        """Все бронирования пользователя."""

    @abstractmethod
    async def get_reservation(self, reservation_uid: UUID, username: str) -> Reservation | None:
        """Бронирование пользователя. None, если его нет или оно принадлежит другому."""

    @abstractmethod
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
        """Создать бронирование. None, если отеля с таким uid нет."""

    @abstractmethod
    async def set_status(
        self, reservation_uid: UUID, username: str, status: ReservationStatus
    ) -> Reservation | None:
        """Сменить статус бронирования пользователя. None, если оно недоступно."""


class SQLAlchemyReservationRepository(ReservationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_hotels(self, *, offset: int, limit: int) -> list[Hotel]:
        result = await self._session.execute(
            select(HotelORM).order_by(HotelORM.id).offset(offset).limit(limit)
        )
        return [row.to_domain() for row in result.scalars()]

    async def count_hotels(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(HotelORM))
        return int(result.scalar_one())

    async def _hotel_row(self, hotel_uid: UUID) -> HotelORM | None:
        result = await self._session.execute(select(HotelORM).where(HotelORM.hotel_uid == hotel_uid))
        return result.scalar_one_or_none()

    async def get_hotel(self, hotel_uid: UUID) -> Hotel | None:
        row = await self._hotel_row(hotel_uid)
        return row.to_domain() if row is not None else None

    async def list_reservations(self, username: str) -> list[Reservation]:
        result = await self._session.execute(
            select(ReservationORM).where(ReservationORM.username == username).order_by(ReservationORM.id)
        )
        return [row.to_domain() for row in result.unique().scalars()]

    async def _reservation_row(self, reservation_uid: UUID, username: str) -> ReservationORM | None:
        result = await self._session.execute(
            select(ReservationORM).where(
                ReservationORM.reservation_uid == reservation_uid,
                ReservationORM.username == username,
            )
        )
        return result.unique().scalar_one_or_none()

    async def get_reservation(self, reservation_uid: UUID, username: str) -> Reservation | None:
        row = await self._reservation_row(reservation_uid, username)
        return row.to_domain() if row is not None else None

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
        hotel = await self._hotel_row(hotel_uid)
        if hotel is None:
            return None
        row = ReservationORM(
            reservation_uid=reservation_uid,
            username=username,
            payment_uid=payment_uid,
            hotel_id=hotel.id,
            status=ReservationStatus.PAID.value,
            start_date=to_timestamp(start_date),
            end_date=to_timestamp(end_date),
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row, ["id", "hotel"])
        return row.to_domain()

    async def set_status(
        self, reservation_uid: UUID, username: str, status: ReservationStatus
    ) -> Reservation | None:
        row = await self._reservation_row(reservation_uid, username)
        if row is None:
            return None
        row.status = status.value
        await self._session.commit()
        await self._session.refresh(row, ["status", "hotel"])
        return row.to_domain()
