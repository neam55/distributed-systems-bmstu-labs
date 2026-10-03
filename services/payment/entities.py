"""Сущности предметной области Payment Service."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class PaymentStatus(StrEnum):
    PAID = "PAID"
    CANCELED = "CANCELED"


@dataclass(slots=True)
class Payment:
    """Операция оплаты бронирования."""

    payment_uid: UUID
    status: PaymentStatus
    price: int
    id: int | None = None
