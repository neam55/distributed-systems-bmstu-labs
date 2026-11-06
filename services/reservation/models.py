"""ORM-модели таблиц hotels и reservation."""

from datetime import UTC, date, datetime, time
from uuid import UUID as PyUUID

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from reservation.entities import Hotel, Reservation, ReservationStatus


def to_timestamp(value: date) -> datetime:
    """Дата -> момент времени для колонки TIMESTAMP WITH TIME ZONE."""
    return datetime.combine(value, time.min, tzinfo=UTC)


def to_date(value: datetime) -> date:
    """Момент времени из базы -> календарная дата без сдвига часового пояса."""
    if value.tzinfo is None:
        return value.date()
    return value.astimezone(UTC).date()


class Base(DeclarativeBase):
    """Базовый класс декларативных моделей сервиса."""


class HotelORM(Base):
    __tablename__ = "hotels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hotel_uid: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(80), nullable=False)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    stars: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price: Mapped[int] = mapped_column(Integer, nullable=False)

    def to_domain(self) -> Hotel:
        return Hotel(
            id=self.id,
            hotel_uid=self.hotel_uid,
            name=self.name,
            country=self.country,
            city=self.city,
            address=self.address,
            stars=self.stars,
            price=self.price,
        )


class ReservationORM(Base):
    __tablename__ = "reservation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reservation_uid: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    payment_uid: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    hotel_id: Mapped[int] = mapped_column(Integer, ForeignKey("hotels.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    hotel: Mapped[HotelORM] = relationship(lazy="joined")

    def to_domain(self) -> Reservation:
        return Reservation(
            id=self.id,
            reservation_uid=self.reservation_uid,
            username=self.username,
            payment_uid=self.payment_uid,
            hotel=self.hotel.to_domain(),
            status=ReservationStatus(self.status),
            start_date=to_date(self.start_date),
            end_date=to_date(self.end_date),
        )


class ReservationCancellationORM(Base):
    """A cancellation intent is scoped to the owner of the operation."""

    __tablename__ = "reservation_cancellation"
    reservation_uid: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False)
