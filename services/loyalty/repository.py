"""Хранилище записей о лояльности."""

from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from loyalty.entities import Loyalty, LoyaltyStatus
from loyalty.models import LoyaltyORM


class LoyaltyRepository(ABC):
    @abstractmethod
    async def get(self, username: str) -> Loyalty | None:
        """Вернуть запись пользователя или None, если её нет."""

    @abstractmethod
    async def add(self, loyalty: Loyalty) -> Loyalty:
        """Создать запись и вернуть её с присвоенным id."""

    @abstractmethod
    async def save_tier(
        self, username: str, reservation_count: int, status: LoyaltyStatus, discount: int
    ) -> Loyalty | None:
        """Записать новый счётчик и уровень. None, если записи пользователя нет."""


class SQLAlchemyLoyaltyRepository(LoyaltyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _row(self, username: str) -> LoyaltyORM | None:
        result = await self._session.execute(select(LoyaltyORM).where(LoyaltyORM.username == username))
        return result.scalar_one_or_none()

    async def get(self, username: str) -> Loyalty | None:
        row = await self._row(username)
        return row.to_domain() if row is not None else None

    async def add(self, loyalty: Loyalty) -> Loyalty:
        row = LoyaltyORM(
            username=loyalty.username,
            reservation_count=loyalty.reservation_count,
            status=loyalty.status.value,
            discount=loyalty.discount,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row.to_domain()

    async def save_tier(
        self, username: str, reservation_count: int, status: LoyaltyStatus, discount: int
    ) -> Loyalty | None:
        row = await self._row(username)
        if row is None:
            return None
        row.reservation_count = reservation_count
        row.status = status.value
        row.discount = discount
        await self._session.commit()
        await self._session.refresh(row)
        return row.to_domain()
