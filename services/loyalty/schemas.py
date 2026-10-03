"""DTO Loyalty Service."""

from common.schemas import CamelModel
from loyalty.entities import LoyaltyStatus


class LoyaltyResponse(CamelModel):
    """Состояние пользователя в программе лояльности."""

    status: LoyaltyStatus
    discount: int
    reservation_count: int


class LoyaltyChangeRequest(CamelModel):
    """Изменение счётчика бронирований: +1 при бронировании, -1 при отмене."""

    delta: int
