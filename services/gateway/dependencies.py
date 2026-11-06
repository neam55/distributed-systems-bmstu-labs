"""Граф зависимостей Gateway."""

from typing import Annotated

from fastapi import Depends, FastAPI, Header, Request

from common.http import ServiceClient
from gateway.circuit_breaker import CircuitBreaker
from gateway.clients import (
    HttpLoyaltyServiceClient,
    HttpPaymentServiceClient,
    HttpReservationServiceClient,
    LoyaltyServiceClient,
    PaymentServiceClient,
    ReservationServiceClient,
)
from gateway.config import get_settings
from gateway.recovery import RecoveryHandler
from gateway.retry_queue import RetryQueue
from gateway.service import BookingService

_settings = get_settings()


def _breaker(name: str) -> CircuitBreaker:
    return CircuitBreaker(name, _settings.cb_failure_threshold, _settings.cb_recovery_timeout)


def get_reservation_client(request: Request) -> ReservationServiceClient:
    """Точка подмены клиента Reservation Service в тестах."""
    return HttpReservationServiceClient(request.app.state.reservation_http)


def get_payment_client(request: Request) -> PaymentServiceClient:
    """Точка подмены клиента Payment Service в тестах."""
    return HttpPaymentServiceClient(request.app.state.payment_http)


def get_loyalty_client(request: Request) -> LoyaltyServiceClient:
    """Точка подмены клиента Loyalty Service в тестах."""
    return HttpLoyaltyServiceClient(request.app.state.loyalty_http)


def get_booking_service(
    request: Request,
    reservations: Annotated[ReservationServiceClient, Depends(get_reservation_client)],
    payments: Annotated[PaymentServiceClient, Depends(get_payment_client)],
    loyalty: Annotated[LoyaltyServiceClient, Depends(get_loyalty_client)],
) -> BookingService:
    return BookingService(reservations, payments, loyalty, getattr(request.app.state, "recovery", None))


async def close_http_clients(app: FastAPI) -> None:
    for client in (app.state.reservation_http, app.state.payment_http, app.state.loyalty_http):
        await client.aclose()


BookingServiceDep = Annotated[BookingService, Depends(get_booking_service)]
UserName = Annotated[str, Header(alias="X-User-Name", description="Имя пользователя")]


def create_recovery_queue(app: FastAPI) -> RetryQueue:
    settings = get_settings()
    app.state.reservation_http = ServiceClient(
        "Reservation",
        settings.reservation_service_url,
        timeout=settings.request_timeout,
        read_guard=_breaker("Reservation"),
    )
    app.state.payment_http = ServiceClient(
        "Payment",
        settings.payment_service_url,
        timeout=settings.request_timeout,
        read_guard=_breaker("Payment"),
    )
    app.state.loyalty_http = ServiceClient(
        "Loyalty",
        settings.loyalty_service_url,
        timeout=settings.request_timeout,
        read_guard=_breaker("Loyalty"),
    )
    handler = RecoveryHandler(
        HttpReservationServiceClient(app.state.reservation_http),
        HttpPaymentServiceClient(app.state.payment_http),
        HttpLoyaltyServiceClient(app.state.loyalty_http),
    )
    return RetryQueue(handler.execute, retry_interval=settings.retry_interval)
