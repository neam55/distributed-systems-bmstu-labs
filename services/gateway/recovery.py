"""Idempotent recovery commands executed independently of HTTP requests."""

from common.errors import NotFoundError
from gateway.clients import LoyaltyServiceClient, PaymentServiceClient, ReservationServiceClient
from gateway.retry_queue import RecoveryKind, RetryJob


class RecoveryHandler:
    def __init__(
        self,
        reservations: ReservationServiceClient,
        payments: PaymentServiceClient,
        loyalty: LoyaltyServiceClient,
    ) -> None:
        self.reservations = reservations
        self.payments = payments
        self.loyalty = loyalty

    async def execute(self, job: RetryJob) -> None:
        if job.kind == RecoveryKind.CANCEL_PAYMENT:
            assert job.payment_uid is not None
            await self.payments.compensate(job.payment_uid)
        elif job.kind == RecoveryKind.CANCEL_RESERVATION:
            assert job.reservation_uid is not None
            await self.reservations.compensate(job.reservation_uid, job.username)
        elif job.kind == RecoveryKind.REVERSE_BOOKING_LOYALTY:
            await self.loyalty.reverse_increment(job.username, job.operation_uid)
        else:
            assert job.reservation_uid is not None
            reservation = await self.reservations.cancel_reservation(job.reservation_uid, job.username)
            if reservation is None:
                raise NotFoundError("Reservation disappeared during cancellation recovery")
            await self.loyalty.change_count(job.username, -1, operation_uid=job.reservation_uid)
