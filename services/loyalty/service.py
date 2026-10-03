"""Бизнес-логика программы лояльности."""

from common.errors import NotFoundError
from loyalty.entities import Loyalty, LoyaltyStatus
from loyalty.repository import LoyaltyRepository

SILVER_THRESHOLD = 10
GOLD_THRESHOLD = 20

DISCOUNTS: dict[LoyaltyStatus, int] = {
    LoyaltyStatus.BRONZE: 5,
    LoyaltyStatus.SILVER: 7,
    LoyaltyStatus.GOLD: 10,
}


def tier_for(reservation_count: int) -> tuple[LoyaltyStatus, int]:
    """Уровень и скидка по количеству бронирований.

    SILVER — после 10 бронирований, GOLD — после 20. Та же таблица применяется и при
    уменьшении счётчика, поэтому понижение уровня происходит автоматически.
    """
    if reservation_count >= GOLD_THRESHOLD:
        status = LoyaltyStatus.GOLD
    elif reservation_count >= SILVER_THRESHOLD:
        status = LoyaltyStatus.SILVER
    else:
        status = LoyaltyStatus.BRONZE
    return status, DISCOUNTS[status]


class LoyaltyService:
    def __init__(self, repository: LoyaltyRepository) -> None:
        self._repository = repository

    async def get_or_create(self, username: str) -> Loyalty:
        """Состояние пользователя; для нового создаётся запись BRONZE со счётчиком 0.

        Создание «на лету» нужно, чтобы первое бронирование нового пользователя
        не падало из-за отсутствия записи в программе лояльности.
        """
        existing = await self._repository.get(username)
        if existing is not None:
            return existing
        status, discount = tier_for(0)
        return await self._repository.add(
            Loyalty(username=username, reservation_count=0, status=status, discount=discount)
        )

    async def change_count(self, username: str, delta: int) -> Loyalty:
        """Изменить счётчик бронирований и пересчитать уровень.

        Счётчик не уходит ниже нуля: отмена брони, созданной вне системы, не должна
        приводить к отрицательному количеству.
        """
        current = await self.get_or_create(username)
        reservation_count = max(0, current.reservation_count + delta)
        status, discount = tier_for(reservation_count)
        updated = await self._repository.save_tier(username, reservation_count, status, discount)
        if updated is None:
            raise NotFoundError(f"Loyalty record for user '{username}' not found")
        return updated
