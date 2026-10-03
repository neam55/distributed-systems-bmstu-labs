"""DTO внешнего API системы. Контракт — [inst][v2] Hotels Booking System.yml."""

from datetime import date
from uuid import UUID

from pydantic import Field

from common.schemas import CamelModel


class HotelResponse(CamelModel):
    hotel_uid: UUID
    name: str
    country: str
    city: str
    address: str
    stars: int | None = None
    price: int


class PaginationResponse(CamelModel):
    page: int
    page_size: int
    total_elements: int
    items: list[HotelResponse]


class HotelInfo(CamelModel):
    """Отель внутри бронирования: адрес уже собран в одну строку."""

    hotel_uid: UUID
    name: str
    full_address: str
    stars: int | None = None


class PaymentInfo(CamelModel):
    status: str
    price: int


class ReservationResponse(CamelModel):
    reservation_uid: UUID
    hotel: HotelInfo
    start_date: date
    end_date: date
    status: str
    payment: PaymentInfo | None = None


class LoyaltyInfoResponse(CamelModel):
    status: str
    discount: int
    reservation_count: int


class UserInfoResponse(CamelModel):
    """Полная информация о пользователе: бронирования и статус лояльности."""

    reservations: list[ReservationResponse]
    loyalty: LoyaltyInfoResponse


class CreateReservationRequest(CamelModel):
    hotel_uid: UUID = Field(examples=["049161bb-badd-4fa8-9d90-87c9a82b0668"])
    start_date: date = Field(examples=["2021-10-08"])
    end_date: date = Field(examples=["2021-10-11"])


class CreateReservationResponse(CamelModel):
    reservation_uid: UUID
    hotel_uid: UUID
    start_date: date
    end_date: date
    discount: int
    status: str
    payment: PaymentInfo
