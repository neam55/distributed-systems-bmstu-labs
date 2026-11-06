"""Хранилище отелей и бронирований."""

from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from reservation.entities import Hotel, Reservation, ReservationStatus
from reservation.models import HotelORM, ReservationCancellationORM, ReservationORM, to_timestamp


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

    @abstractmethod
    async def compensate(self, reservation_uid: UUID, username: str) -> None:
        """Cancel an operation, including one whose create is still in flight."""


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
            select(ReservationORM)
            .where(ReservationORM.username == username, self._not_compensated())
            .order_by(ReservationORM.id)
        )
        return [row.to_domain() for row in result.unique().scalars()]

    async def _reservation_row(self, reservation_uid: UUID, username: str) -> ReservationORM | None:
        result = await self._session.execute(
            select(ReservationORM).where(
                ReservationORM.reservation_uid == reservation_uid,
                ReservationORM.username == username,
                self._not_compensated(),
            )
        )
        return result.unique().scalar_one_or_none()

    @staticmethod
    def _not_compensated() -> ColumnElement[bool]:
        return (
            ~select(ReservationCancellationORM.reservation_uid)
            .where(ReservationCancellationORM.reservation_uid == ReservationORM.reservation_uid)
            .exists()
        )

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
        await self._lock(reservation_uid)
        existing_result = await self._session.execute(
            select(ReservationORM).where(ReservationORM.reservation_uid == reservation_uid)
        )
        existing = existing_result.unique().scalar_one_or_none()
        if existing is not None:
            current = existing.to_domain()
            if (
                current.username,
                current.payment_uid,
                current.hotel.hotel_uid,
                current.start_date,
                current.end_date,
            ) != (username, payment_uid, hotel_uid, start_date, end_date):
                raise HTTPException(status_code=409, detail="Reservation UID payload conflict")
            await self._session.commit()
            return current
        canceled = await self._session.get(ReservationCancellationORM, reservation_uid)
        if canceled is not None and canceled.username != username:
            raise HTTPException(status_code=409, detail="Reservation UID owner conflict")
        hotel = await self._hotel_row(hotel_uid)
        if hotel is None:
            return None
        row = ReservationORM(
            reservation_uid=reservation_uid,
            username=username,
            payment_uid=payment_uid,
            hotel_id=hotel.id,
            status=ReservationStatus.CANCELED.value if canceled else ReservationStatus.PAID.value,
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

    async def _lock(self, reservation_uid: UUID) -> None:
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"reservation:{reservation_uid}"},
        )

    async def compensate(self, reservation_uid: UUID, username: str) -> None:
        await self._lock(reservation_uid)
        result = await self._session.execute(
            select(ReservationORM).where(ReservationORM.reservation_uid == reservation_uid)
        )
        row = result.unique().scalar_one_or_none()
        intent = await self._session.get(ReservationCancellationORM, reservation_uid)
        if (row is not None and row.username != username) or (
            intent is not None and intent.username != username
        ):
            raise HTTPException(status_code=404, detail="Reservation not found")
        if intent is None:
            self._session.add(ReservationCancellationORM(reservation_uid=reservation_uid, username=username))
        if row is not None:
            row.status = ReservationStatus.CANCELED.value
        await self._session.commit()
