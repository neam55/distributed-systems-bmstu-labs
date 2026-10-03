"""REST API Reservation Service: справочник отелей и бронирования."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from common.schemas import ErrorResponse, Responses
from reservation.dependencies import ReservationServiceDep, UserName
from reservation.schemas import (
    CreateReservationRequest,
    HotelResponse,
    PaginationResponse,
    ReservationResponse,
)

hotels_router = APIRouter(prefix="/api/v1/hotels", tags=["Hotels API"])
reservations_router = APIRouter(prefix="/api/v1/reservations", tags=["Reservations API"])

HOTEL_NOT_FOUND: Responses = {404: {"model": ErrorResponse, "description": "Отель не найден"}}
RESERVATION_NOT_FOUND: Responses = {404: {"model": ErrorResponse, "description": "Бронирование не найдено"}}

Page = Annotated[int, Query(ge=1, description="Номер страницы, нумерация с единицы")]
Size = Annotated[int, Query(ge=1, le=100, description="Количество элементов на странице")]


@hotels_router.get("", response_model=PaginationResponse, summary="Получить список отелей")
async def list_hotels(service: ReservationServiceDep, page: Page = 1, size: Size = 10) -> PaginationResponse:
    return PaginationResponse.model_validate(await service.list_hotels(page, size))


@hotels_router.get(
    "/{hotel_uid}",
    response_model=HotelResponse,
    summary="Получить отель по UUID",
    responses=HOTEL_NOT_FOUND,
)
async def get_hotel(hotel_uid: UUID, service: ReservationServiceDep) -> HotelResponse:
    return HotelResponse.model_validate(await service.get_hotel(hotel_uid))


@reservations_router.get(
    "",
    response_model=list[ReservationResponse],
    summary="Бронирования пользователя",
)
async def list_reservations(
    service: ReservationServiceDep, x_user_name: UserName
) -> list[ReservationResponse]:
    reservations = await service.list_reservations(x_user_name)
    return [ReservationResponse.model_validate(item) for item in reservations]


@reservations_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ReservationResponse,
    summary="Создать бронирование",
    responses=HOTEL_NOT_FOUND,
)
async def create_reservation(
    payload: CreateReservationRequest, service: ReservationServiceDep
) -> ReservationResponse:
    reservation = await service.create_reservation(
        username=payload.username,
        payment_uid=payload.payment_uid,
        hotel_uid=payload.hotel_uid,
        start_date=payload.start_date,
        end_date=payload.end_date,
    )
    return ReservationResponse.model_validate(reservation)


@reservations_router.get(
    "/{reservation_uid}",
    response_model=ReservationResponse,
    summary="Бронирование по UUID",
    description="Бронирование другого пользователя неотличимо от отсутствующего: 404.",
    responses=RESERVATION_NOT_FOUND,
)
async def get_reservation(
    reservation_uid: UUID, service: ReservationServiceDep, x_user_name: UserName
) -> ReservationResponse:
    return ReservationResponse.model_validate(await service.get_reservation(reservation_uid, x_user_name))


@reservations_router.post(
    "/{reservation_uid}/cancel",
    response_model=ReservationResponse,
    summary="Отменить бронирование",
    description="Переводит бронирование в статус CANCELED и возвращает его вместе с paymentUid.",
    responses=RESERVATION_NOT_FOUND,
)
async def cancel_reservation(
    reservation_uid: UUID, service: ReservationServiceDep, x_user_name: UserName
) -> ReservationResponse:
    return ReservationResponse.model_validate(
        await service.cancel_reservation(reservation_uid, x_user_name)
    )
