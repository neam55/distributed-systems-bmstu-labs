"""Сущности предметной области Loyalty Service."""

from dataclasses import dataclass
from enum import StrEnum


class LoyaltyStatus(StrEnum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"


def tier_for(reservation_count: int) -> tuple[LoyaltyStatus, int]:
    """Уровень и скидка по количеству бронирований, включая понижение уровня."""
    if reservation_count >= 20:
        return LoyaltyStatus.GOLD, 10
    if reservation_count >= 10:
        return LoyaltyStatus.SILVER, 7
    return LoyaltyStatus.BRONZE, 5


@dataclass(slots=True)
class Loyalty:
    """Запись о участии пользователя в программе лояльности."""

    username: str
    reservation_count: int
    status: LoyaltyStatus
    discount: int
    id: int | None = None
