from collections.abc import Sequence
from dataclasses import replace
from uuid import UUID

from payment.entities import Payment, PaymentStatus
from payment.repository import PaymentRepository


class InMemoryPaymentRepository(PaymentRepository):
    """Хранилище платежей в памяти."""

    def __init__(self) -> None:
        self._storage: dict[UUID, Payment] = {}
        self._next_id = 1

    async def add(self, payment: Payment) -> Payment:
        stored = replace(payment, id=self._next_id)
        self._next_id += 1
        self._storage[stored.payment_uid] = stored
        return replace(stored)

    async def get(self, payment_uid: UUID) -> Payment | None:
        found = self._storage.get(payment_uid)
        return replace(found) if found is not None else None

    async def list_by_uids(self, payment_uids: Sequence[UUID]) -> list[Payment]:
        return [replace(self._storage[uid]) for uid in payment_uids if uid in self._storage]

    async def set_status(self, payment_uid: UUID, status: PaymentStatus) -> Payment | None:
        found = self._storage.get(payment_uid)
        if found is None:
            return None
        updated = replace(found, status=status)
        self._storage[payment_uid] = updated
        return replace(updated)
