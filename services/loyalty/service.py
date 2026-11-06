"""Бизнес-логика программы лояльности."""

from uuid import UUID

from common.errors import NotFoundError
from loyalty.entities import Loyalty, tier_for
from loyalty.repository import LoyaltyRepository


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

    async def change_count(self, username: str, delta: int, operation_uid: UUID | None = None) -> Loyalty:
        """Изменить счётчик бронирований и пересчитать уровень.

        Счётчик не уходит ниже нуля: отмена брони, созданной вне системы, не должна
        приводить к отрицательному количеству.
        """
        await self.get_or_create(username)
        updated = await self._repository.change_count(username, delta, operation_uid)
        if updated is None:
            raise NotFoundError(f"Loyalty record for user '{username}' not found")
        return updated

    async def reverse_increment(self, username: str, operation_uid: UUID) -> Loyalty:
        await self.get_or_create(username)
        updated = await self._repository.reverse_increment(username, operation_uid)
        if updated is None:
            raise NotFoundError(f"Loyalty record for user {username!r} not found")
        return updated
