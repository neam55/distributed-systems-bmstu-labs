"""Внешний REST API системы. Единая точка входа для пользователя."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from common.schemas import ErrorResponse, Responses, ValidationErrorResponse
from gateway.dependencies import BookingServiceDep, UserName
from gateway.schemas import (
    CreateReservationRequest,
    CreateReservationResponse,
    LoyaltyInfoResponse,
    PaginationResponse,
    ReservationResponse,
    UserInfoResponse,
)

router = APIRouter(prefix="/api/v1", tags=["Gateway API"])

RESERVATION_NOT_FOUND: Responses = {404: {"model": ErrorResponse, "description": "Бронирование не найдено"}}

Page = Annotated[int, Query(ge=0, description="Номер страницы; 0 и 1 обозначают первую страницу")]
Size = Annotated[int, Query(ge=1, le=100, description="Количество элементов на странице")]


@router.get("/hotels", response_model=PaginationResponse, summary="Получить список отелей")
async def list_hotels(service: BookingServiceDep, page: Page = 1, size: Size = 10) -> PaginationResponse:
    return await service.list_hotels(page, size)


@router.get("/me", response_model=UserInfoResponse, summary="Информация о пользователе")
async def get_me(service: BookingServiceDep, x_user_name: UserName) -> UserInfoResponse:
    return await service.get_user_info(x_user_name)


@router.get(
    "/loyalty",
    response_model=LoyaltyInfoResponse,
    summary="Получить информацию о статусе в программе лояльности",
)
async def get_loyalty(service: BookingServiceDep, x_user_name: UserName) -> LoyaltyInfoResponse:
    return await service.get_loyalty(x_user_name)


@router.get(
    "/reservations",
    response_model=list[ReservationResponse],
    summary="Информация по всем бронированиям пользователя",
)
async def list_reservations(service: BookingServiceDep, x_user_name: UserName) -> list[ReservationResponse]:
    return await service.list_reservations(x_user_name)


@router.post(
    "/reservations",
    response_model=CreateReservationResponse,
    summary="Забронировать отель",
    description=(
        "Проверяет отель, получает скидку в Loyalty Service, создаёт оплату в Payment Service, "
        "создаёт бронирование и увеличивает счётчик бронирований."
    ),
    responses={
        400: {"model": ValidationErrorResponse, "description": "Ошибка валидации данных"},
        404: {"model": ErrorResponse, "description": "Отель не найден"},
    },
)
async def create_reservation(
    payload: CreateReservationRequest,
    service: BookingServiceDep,
    x_user_name: UserName,
) -> CreateReservationResponse:
    return await service.book(x_user_name, payload)


@router.get(
    "/reservations/{reservation_uid}",
    response_model=ReservationResponse,
    summary="Информация по конкретному бронированию",
    responses=RESERVATION_NOT_FOUND,
)
async def get_reservation(
    reservation_uid: UUID, service: BookingServiceDep, x_user_name: UserName
) -> ReservationResponse:
    return await service.get_reservation(reservation_uid, x_user_name)


@router.delete(
    "/reservations/{reservation_uid}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Отменить бронирование",
    description=(
        "Бронирование и оплата помечаются CANCELED, счётчик бронирований уменьшается "
        "с возможным понижением статуса лояльности."
    ),
    responses={
        204: {"description": "Бронь успешно отменена"},
        **RESERVATION_NOT_FOUND,
    },
)
async def cancel_reservation(
    reservation_uid: UUID, service: BookingServiceDep, x_user_name: UserName
) -> Response:
    await service.cancel(reservation_uid, x_user_name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
