"""Сущности предметной области Reservation Service."""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from uuid import UUID


class ReservationStatus(StrEnum):
    PAID = "PAID"
    CANCELED = "CANCELED"


@dataclass(slots=True)
class Hotel:
    """Отель из справочника сервиса."""

    hotel_uid: UUID
    name: str
    country: str
    city: str
    address: str
    price: int
    stars: int | None = None
    id: int | None = None

    @property
    def full_address(self) -> str:
        """Полный адрес в виде «страна, город, адрес» — так его ждёт контракт."""
        return f"{self.country}, {self.city}, {self.address}"


@dataclass(slots=True)
class Reservation:
    """Бронирование отеля пользователем."""

    reservation_uid: UUID
    username: str
    payment_uid: UUID
    hotel: Hotel
    status: ReservationStatus
    start_date: date
    end_date: date
    id: int | None = None


@dataclass(slots=True)
class HotelPage:
    """Страница справочника отелей."""

    page: int
    total_elements: int
    items: list[Hotel] = field(default_factory=list)

    @property
    def page_size(self) -> int:
        """Фактическое число элементов на странице (всегда не больше запрошенного size)."""
        return len(self.items)
