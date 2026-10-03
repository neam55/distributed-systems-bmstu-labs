"""Сущности предметной области Loyalty Service."""

from dataclasses import dataclass
from enum import StrEnum


class LoyaltyStatus(StrEnum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"


@dataclass(slots=True)
class Loyalty:
    """Запись о участии пользователя в программе лояльности."""

    username: str
    reservation_count: int
    status: LoyaltyStatus
    discount: int
    id: int | None = None
