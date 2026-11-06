"""Хранилище платежей."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from payment.entities import Payment, PaymentStatus
from payment.models import PaymentCancellationORM, PaymentORM


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

    @abstractmethod
    async def compensate(self, payment_uid: UUID) -> None:
        """Persist cancellation even if creation has not arrived yet."""


class SQLAlchemyPaymentRepository(PaymentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _row(self, payment_uid: UUID) -> PaymentORM | None:
        result = await self._session.execute(select(PaymentORM).where(PaymentORM.payment_uid == payment_uid))
        return result.scalar_one_or_none()

    async def add(self, payment: Payment) -> Payment:
        await self._lock(payment.payment_uid)
        existing = await self._row(payment.payment_uid)
        if existing is not None:
            if existing.price != payment.price:
                raise HTTPException(status_code=409, detail="Payment UID payload conflict")
            await self._session.commit()
            return existing.to_domain()
        canceled = await self._session.get(PaymentCancellationORM, payment.payment_uid)
        row = PaymentORM(
            payment_uid=payment.payment_uid,
            status=PaymentStatus.CANCELED.value if canceled else payment.status.value,
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

    async def _lock(self, payment_uid: UUID) -> None:
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"payment:{payment_uid}"},
        )

    async def compensate(self, payment_uid: UUID) -> None:
        await self._lock(payment_uid)
        if await self._session.get(PaymentCancellationORM, payment_uid) is None:
            self._session.add(PaymentCancellationORM(payment_uid=payment_uid))
        row = await self._row(payment_uid)
        if row is not None:
            row.status = PaymentStatus.CANCELED.value
        await self._session.commit()
