"""Бизнес-логика Payment Service."""

from collections.abc import Sequence
from uuid import UUID, uuid4

from common.errors import NotFoundError
from payment.entities import Payment, PaymentStatus
from payment.repository import PaymentRepository


class PaymentService:
    def __init__(self, repository: PaymentRepository) -> None:
        self._repository = repository

    async def create(self, price: int) -> Payment:
        """Создать оплаченный платёж. Сумма уже посчитана Gateway со скидкой."""
        return await self._repository.add(
            Payment(payment_uid=uuid4(), status=PaymentStatus.PAID, price=price)
        )

    async def get(self, payment_uid: UUID) -> Payment:
        payment = await self._repository.get(payment_uid)
        if payment is None:
            raise NotFoundError(f"Payment with uid {payment_uid} not found")
        return payment

    async def list_by_uids(self, payment_uids: Sequence[UUID]) -> list[Payment]:
        return await self._repository.list_by_uids(payment_uids)

    async def cancel(self, payment_uid: UUID) -> Payment:
        canceled = await self._repository.set_status(payment_uid, PaymentStatus.CANCELED)
        if canceled is None:
            raise NotFoundError(f"Payment with uid {payment_uid} not found")
        return canceled
