"""REST API Payment Service."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from common.schemas import ErrorResponse, Responses
from payment.dependencies import PaymentServiceDep
from payment.schemas import CreatePaymentRequest, PaymentResponse

router = APIRouter(prefix="/api/v1/payments", tags=["Payment API"])

NOT_FOUND: Responses = {404: {"model": ErrorResponse, "description": "Платёж не найден"}}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=PaymentResponse,
    summary="Создать запись об оплате",
)
async def create_payment(payload: CreatePaymentRequest, service: PaymentServiceDep) -> PaymentResponse:
    payment = await service.create(payload.price)
    return PaymentResponse.model_validate(payment)


@router.get(
    "",
    response_model=list[PaymentResponse],
    summary="Получить платежи по списку uid",
    description="Батч-выборка: позволяет Gateway собрать список бронирований без N+1 запросов.",
)
async def list_payments(
    service: PaymentServiceDep,
    uids: Annotated[list[UUID], Query(description="UUID платежей")] = [],  # noqa: B006
) -> list[PaymentResponse]:
    payments = await service.list_by_uids(uids)
    return [PaymentResponse.model_validate(payment) for payment in payments]


@router.get(
    "/{payment_uid}",
    response_model=PaymentResponse,
    summary="Получить платёж",
    responses=NOT_FOUND,
)
async def get_payment(payment_uid: UUID, service: PaymentServiceDep) -> PaymentResponse:
    return PaymentResponse.model_validate(await service.get(payment_uid))


@router.post(
    "/{payment_uid}/cancel",
    response_model=PaymentResponse,
    summary="Отменить платёж",
    description="Переводит платёж в статус CANCELED при отмене бронирования.",
    responses=NOT_FOUND,
)
async def cancel_payment(payment_uid: UUID, service: PaymentServiceDep) -> PaymentResponse:
    return PaymentResponse.model_validate(await service.cancel(payment_uid))
