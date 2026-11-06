"""Хранилище записей о лояльности."""

from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from loyalty.entities import Loyalty, tier_for
from loyalty.models import LoyaltyOperationORM, LoyaltyORM


class LoyaltyRepository(ABC):
    @abstractmethod
    async def get(self, username: str) -> Loyalty | None:
        """Вернуть запись пользователя или None, если её нет."""

    @abstractmethod
    async def add(self, loyalty: Loyalty) -> Loyalty:
        """Создать запись и вернуть её с присвоенным id."""

    @abstractmethod
    async def change_count(
        self, username: str, delta: int, operation_uid: UUID | None = None
    ) -> Loyalty | None:
        """Атомарно изменить счётчик; operation_uid защищает от повторного применения."""


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

    async def change_count(
        self, username: str, delta: int, operation_uid: UUID | None = None
    ) -> Loyalty | None:
        result = await self._session.execute(
            select(LoyaltyORM)
            .where(LoyaltyORM.username == username)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        if operation_uid is not None:
            operation = await self._session.get(LoyaltyOperationORM, (username, operation_uid))
            if operation is not None:
                await self._session.commit()
                return row.to_domain()
            self._session.add(LoyaltyOperationORM(username=username, operation_uid=operation_uid))
        reservation_count = max(0, row.reservation_count + delta)
        status, discount = tier_for(reservation_count)
        row.reservation_count = reservation_count
        row.status = status.value
        row.discount = discount
        await self._session.commit()
        await self._session.refresh(row)
        return row.to_domain()
