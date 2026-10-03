"""Хранилище платежей."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from payment.entities import Payment, PaymentStatus
from payment.models import PaymentORM


class PaymentRepository(ABC):
    @abstractmethod
    async def add(self, payment: Payment) -> Payment:
        """Сохранить платёж."""

    @abstractmethod
    async def get(self, payment_uid: UUID) -> Payment | None:
        """Вернуть платёж по его uid или None."""

    @abstractmethod
    async def list_by_uids(self, payment_uids: Sequence[UUID]) -> list[Payment]:
        """Вернуть платежи по списку uid: одним запросом вместо N отдельных."""

    @abstractmethod
    async def set_status(self, payment_uid: UUID, status: PaymentStatus) -> Payment | None:
        """Сменить статус платежа. None, если платежа нет."""


class SQLAlchemyPaymentRepository(PaymentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _row(self, payment_uid: UUID) -> PaymentORM | None:
        result = await self._session.execute(
            select(PaymentORM).where(PaymentORM.payment_uid == payment_uid)
        )
        return result.scalar_one_or_none()

    async def add(self, payment: Payment) -> Payment:
        row = PaymentORM(
            payment_uid=payment.payment_uid,
            status=payment.status.value,
            price=payment.price,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return row.to_domain()

    async def get(self, payment_uid: UUID) -> Payment | None:
        row = await self._row(payment_uid)
        return row.to_domain() if row is not None else None

    async def list_by_uids(self, payment_uids: Sequence[UUID]) -> list[Payment]:
        if not payment_uids:
            return []
        result = await self._session.execute(
            select(PaymentORM).where(PaymentORM.payment_uid.in_(payment_uids))
        )
        return [row.to_domain() for row in result.scalars()]

    async def set_status(self, payment_uid: UUID, status: PaymentStatus) -> Payment | None:
        row = await self._row(payment_uid)
        if row is None:
            return None
        row.status = status.value
        await self._session.commit()
        await self._session.refresh(row)
        return row.to_domain()
