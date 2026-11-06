"""Оркестрация сценариев системы.

Gateway — единственное место, где вызовы сервисов соединяются в один сценарий;
горизонтальные вызовы между сервисами запрещены.
"""

from uuid import UUID, uuid4

from common.errors import NotFoundError, UpstreamError, ValidationError
from gateway.clients import (
    LoyaltyServiceClient,
    PaymentData,
    PaymentServiceClient,
    ReservationData,
    ReservationServiceClient,
)
from gateway.recovery import RecoveryHandler
from gateway.retry_queue import RecoveryKind, RetryJob, RetryQueue
from gateway.schemas import (
    CreateReservationRequest,
    CreateReservationResponse,
    EmptyInfo,
    HotelInfo,
    LoyaltyInfoResponse,
    PaginationResponse,
    PaymentInfo,
    ReservationResponse,
    UserInfoResponse,
)


def apply_discount(price: int, discount: int) -> int:
    """Сумма со скидкой в процентах. Целочисленно: цены в копейках не хранятся."""
    return price - price * discount // 100


class BookingService:
    def __init__(
        self,
        reservations: ReservationServiceClient,
        payments: PaymentServiceClient,
        loyalty: LoyaltyServiceClient,
        recovery: RetryQueue | None = None,
    ) -> None:
        self._reservations = reservations
        self._payments = payments
        self._loyalty = loyalty
        self._handler = RecoveryHandler(reservations, payments, loyalty)
        self.recovery = recovery if recovery is not None else RetryQueue(self._handler.execute)

    async def list_hotels(self, page: int, size: int) -> PaginationResponse:
        page_data = await self._reservations.list_hotels(page, size)
        return PaginationResponse.model_validate(page_data.model_dump())

    async def get_loyalty(self, username: str) -> LoyaltyInfoResponse:
        loyalty = await self._loyalty.get(username)
        return LoyaltyInfoResponse.model_validate(loyalty.model_dump())

    async def list_reservations(self, username: str) -> list[ReservationResponse]:
        reservations = await self._reservations.list_reservations(username)
        payments = (
            await self._read_payments([item.payment_uid for item in reservations]) if reservations else []
        )
        by_uid = {payment.payment_uid: payment for payment in payments}
        return [self._to_response(item, by_uid.get(item.payment_uid)) for item in reservations]

    async def get_reservation(self, reservation_uid: UUID, username: str) -> ReservationResponse:
        reservation = await self._reservations.get_reservation(reservation_uid, username)
        if reservation is None:
            raise NotFoundError(f"Reservation with uid {reservation_uid} not found")
        payments = await self._read_payments([reservation.payment_uid])
        return self._to_response(reservation, payments[0] if payments else None)

    async def get_user_info(self, username: str) -> UserInfoResponse:
        reservations = await self.list_reservations(username)
        loyalty: LoyaltyInfoResponse | EmptyInfo
        try:
            loyalty = await self.get_loyalty(username)
        except UpstreamError as exc:
            if not exc.retryable:
                raise
            loyalty = EmptyInfo()
        return UserInfoResponse(reservations=reservations, loyalty=loyalty)

    async def _read_payments(self, uids: list[UUID]) -> list[PaymentData]:
        try:
            return await self._payments.list_by_uids(uids)
        except UpstreamError as exc:
            if not exc.retryable:
                raise
            return []

    async def book(self, username: str, request: CreateReservationRequest) -> CreateReservationResponse:
        """Сценарий бронирования: отель -> скидка -> оплата -> бронь -> счётчик лояльности."""
        nights = (request.end_date - request.start_date).days
        if nights <= 0:
            raise ValidationError(
                "Validation failed",
                {"endDate": "endDate must be later than startDate"},
            )

        hotel = await self._reservations.get_hotel(request.hotel_uid)
        if hotel is None:
            raise NotFoundError(f"Hotel with uid {request.hotel_uid} not found")

        loyalty = await self._loyalty.get(username)
        total_price = apply_discount(hotel.price * nights, loyalty.discount)

        payment_uid, reservation_uid, operation_uid = uuid4(), uuid4(), uuid4()
        reservation_attempted = loyalty_attempted = False
        try:
            payment = await self._payments.create(total_price, payment_uid=payment_uid)
            reservation_attempted = True
            reservation = await self._reservations.create_reservation(
                username=username,
                payment_uid=payment_uid,
                hotel_uid=request.hotel_uid,
                start_date=request.start_date,
                end_date=request.end_date,
                reservation_uid=reservation_uid,
            )
            loyalty_attempted = True
            await self._loyalty.change_count(username, 1, operation_uid=operation_uid)
        except UpstreamError:
            jobs = [RetryJob(RecoveryKind.CANCEL_PAYMENT, username, payment_uid, payment_uid=payment_uid)]
            if reservation_attempted:
                jobs.append(
                    RetryJob(
                        RecoveryKind.CANCEL_RESERVATION,
                        username,
                        reservation_uid,
                        reservation_uid=reservation_uid,
                    )
                )
            if loyalty_attempted:
                jobs.append(RetryJob(RecoveryKind.REVERSE_BOOKING_LOYALTY, username, operation_uid))
            for job in jobs:
                try:
                    await self._handler.execute(job)
                except UpstreamError as exc:
                    if exc.retryable:
                        await self.recovery.enqueue(job, delay=True)
            raise

        return CreateReservationResponse(
            reservation_uid=reservation.reservation_uid,
            hotel_uid=hotel.hotel_uid,
            start_date=reservation.start_date,
            end_date=reservation.end_date,
            discount=loyalty.discount,
            status=reservation.status,
            payment=PaymentInfo(status=payment.status, price=payment.price),
        )

    async def cancel(self, reservation_uid: UUID, username: str) -> None:
        """Отмена: бронь -> оплата -> счётчик лояльности (возможно понижение статуса)."""
        reservation = await self._reservations.get_reservation(reservation_uid, username)
        if reservation is None:
            raise NotFoundError(f"Reservation with uid {reservation_uid} not found")
        await self._payments.cancel(reservation.payment_uid)
        job = RetryJob(
            RecoveryKind.COMPLETE_CANCELLATION,
            username,
            reservation_uid,
            reservation_uid=reservation_uid,
        )
        try:
            await self._reservations.cancel_reservation(reservation_uid, username)
        except UpstreamError as exc:
            if exc.retryable:
                await self.recovery.enqueue(job, delay=True)
            raise
        try:
            await self._loyalty.change_count(username, -1, operation_uid=reservation_uid)
        except UpstreamError as exc:
            if not exc.retryable:
                raise
            await self.recovery.enqueue(job, delay=True)

    @staticmethod
    def _to_response(reservation: ReservationData, payment: PaymentData | None) -> ReservationResponse:
        return ReservationResponse(
            reservation_uid=reservation.reservation_uid,
            hotel=HotelInfo.model_validate(reservation.hotel.model_dump()),
            start_date=reservation.start_date,
            end_date=reservation.end_date,
            status=reservation.status,
            payment=PaymentInfo(status=payment.status, price=payment.price) if payment else EmptyInfo(),
        )
