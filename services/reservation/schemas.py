"""DTO Reservation Service."""

from datetime import date
from uuid import UUID

from common.schemas import CamelModel
from reservation.entities import ReservationStatus


class HotelResponse(CamelModel):
    """Отель в справочнике."""

    hotel_uid: UUID
    name: str
    country: str
    city: str
    address: str
    stars: int | None = None
    price: int


class PaginationResponse(CamelModel):
    """Страница справочника отелей."""

    page: int
    page_size: int
    total_elements: int
    items: list[HotelResponse]


class HotelInfo(CamelModel):
    """Краткая информация об отеле внутри бронирования."""

    hotel_uid: UUID
    name: str
    full_address: str
    stars: int | None = None


class ReservationResponse(CamelModel):
    """Бронирование. paymentUid нужен Gateway, чтобы дотянуть данные об оплате."""

    reservation_uid: UUID
    payment_uid: UUID
    hotel: HotelInfo
    start_date: date
    end_date: date
    status: ReservationStatus


class CreateReservationRequest(CamelModel):
    """Запрос на создание брони. Сумму и скидку считает Gateway."""

    username: str
    payment_uid: UUID
    hotel_uid: UUID
    start_date: date
    end_date: date
