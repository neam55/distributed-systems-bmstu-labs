"""Граф зависимостей Gateway."""

from typing import Annotated

from fastapi import Depends, Header

from common.http import ServiceClient
from gateway.clients import (
    HttpLoyaltyServiceClient,
    HttpPaymentServiceClient,
    HttpReservationServiceClient,
    LoyaltyServiceClient,
    PaymentServiceClient,
    ReservationServiceClient,
)
from gateway.config import get_settings
from gateway.service import BookingService

_settings = get_settings()

_reservation_http = ServiceClient(
    "Reservation", _settings.reservation_service_url, timeout=_settings.request_timeout
)
_payment_http = ServiceClient("Payment", _settings.payment_service_url, timeout=_settings.request_timeout)
_loyalty_http = ServiceClient("Loyalty", _settings.loyalty_service_url, timeout=_settings.request_timeout)


def get_reservation_client() -> ReservationServiceClient:
    """Точка подмены клиента Reservation Service в тестах."""
    return HttpReservationServiceClient(_reservation_http)


def get_payment_client() -> PaymentServiceClient:
    """Точка подмены клиента Payment Service в тестах."""
    return HttpPaymentServiceClient(_payment_http)


def get_loyalty_client() -> LoyaltyServiceClient:
    """Точка подмены клиента Loyalty Service в тестах."""
    return HttpLoyaltyServiceClient(_loyalty_http)


def get_booking_service(
    reservations: Annotated[ReservationServiceClient, Depends(get_reservation_client)],
    payments: Annotated[PaymentServiceClient, Depends(get_payment_client)],
    loyalty: Annotated[LoyaltyServiceClient, Depends(get_loyalty_client)],
) -> BookingService:
    return BookingService(reservations, payments, loyalty)


async def close_http_clients() -> None:
    """Закрывает пулы соединений при остановке приложения."""
    for client in (_reservation_http, _payment_http, _loyalty_http):
        await client.aclose()


BookingServiceDep = Annotated[BookingService, Depends(get_booking_service)]
UserName = Annotated[str, Header(alias="X-User-Name", description="Имя пользователя")]
