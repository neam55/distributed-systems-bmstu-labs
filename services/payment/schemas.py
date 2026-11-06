"""DTO Payment Service."""

from uuid import UUID

from pydantic import Field

from common.schemas import CamelModel
from payment.entities import PaymentStatus


class CreatePaymentRequest(CamelModel):
    """Сумма к оплате; скидка уже применена вызывающей стороной."""

    payment_uid: UUID | None = None
    price: int = Field(ge=0, examples=[27000])


class PaymentResponse(CamelModel):
    """Платёж."""

    payment_uid: UUID
    status: PaymentStatus
    price: int
