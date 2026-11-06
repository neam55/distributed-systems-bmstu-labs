"""Фейковые клиенты соседних сервисов.

Все вызовы пишутся в общий список calls — это позволяет проверить не только результат
сценария, но и порядок обращений к сервисам.
"""

from collections.abc import Sequence
from datetime import date
from uuid import UUID, uuid4

from gateway.clients import (
    HotelData,
    HotelInfoData,
    HotelPageData,
    LoyaltyData,
    LoyaltyServiceClient,
    PaymentData,
    PaymentServiceClient,
    ReservationData,
    ReservationServiceClient,
)


class FakeReservationServiceClient(ReservationServiceClient):
    def __init__(self, hotels: list[HotelData], calls: list[str]) -> None:
        self._hotels = {hotel.hotel_uid: hotel for hotel in hotels}
        self._calls = calls
        self.reservations: dict[UUID, ReservationData] = {}
        self.owners: dict[UUID, str] = {}

    async def list_hotels(self, page: int, size: int) -> HotelPageData:
        self._calls.append("reservation.list_hotels")
        offset = max(0, page - 1) * size
        items = list(self._hotels.values())[offset : offset + size]
        return HotelPageData(
            page=page,
            page_size=len(items),
            total_elements=len(self._hotels),
            items=items,
        )

    async def get_hotel(self, hotel_uid: UUID) -> HotelData | None:
        self._calls.append("reservation.get_hotel")
        return self._hotels.get(hotel_uid)

    async def list_reservations(self, username: str) -> list[ReservationData]:
        self._calls.append("reservation.list_reservations")
        return [
            reservation
            for uid, reservation in self.reservations.items()
            if self.owners.get(uid) == username
        ]

    async def get_reservation(self, reservation_uid: UUID, username: str) -> ReservationData | None:
        self._calls.append("reservation.get_reservation")
        if self.owners.get(reservation_uid) != username:
            return None
        return self.reservations.get(reservation_uid)

    async def create_reservation(
        self,
        *,
        username: str,
        payment_uid: UUID,
        hotel_uid: UUID,
        start_date: date,
        end_date: date,
    ) -> ReservationData:
        self._calls.append("reservation.create_reservation")
        hotel = self._hotels[hotel_uid]
        reservation = ReservationData(
            reservation_uid=uuid4(),
            payment_uid=payment_uid,
            hotel=HotelInfoData(
                hotel_uid=hotel.hotel_uid,
                name=hotel.name,
                full_address=f"{hotel.country}, {hotel.city}, {hotel.address}",
                stars=hotel.stars,
            ),
            start_date=start_date,
            end_date=end_date,
            status="PAID",
        )
        self.reservations[reservation.reservation_uid] = reservation
        self.owners[reservation.reservation_uid] = username
        return reservation

    async def cancel_reservation(self, reservation_uid: UUID, username: str) -> ReservationData | None:
        self._calls.append("reservation.cancel_reservation")
        if self.owners.get(reservation_uid) != username:
            return None
        current = self.reservations[reservation_uid]
        canceled = current.model_copy(update={"status": "CANCELED"})
        self.reservations[reservation_uid] = canceled
        return canceled


class FakePaymentServiceClient(PaymentServiceClient):
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls
        self.payments: dict[UUID, PaymentData] = {}

    async def create(self, price: int) -> PaymentData:
        self._calls.append(f"payment.create({price})")
        payment = PaymentData(payment_uid=uuid4(), status="PAID", price=price)
        self.payments[payment.payment_uid] = payment
        return payment

    async def list_by_uids(self, payment_uids: Sequence[UUID]) -> list[PaymentData]:
        self._calls.append("payment.list_by_uids")
        return [self.payments[uid] for uid in payment_uids if uid in self.payments]

    async def cancel(self, payment_uid: UUID) -> PaymentData | None:
        self._calls.append("payment.cancel")
        current = self.payments.get(payment_uid)
        if current is None:
            return None
        canceled = current.model_copy(update={"status": "CANCELED"})
        self.payments[payment_uid] = canceled
        return canceled


class FakeLoyaltyServiceClient(LoyaltyServiceClient):
    def __init__(self, calls: list[str], reservation_count: int = 25) -> None:
        self._calls = calls
        self.reservation_count = reservation_count
        self._operations: set[tuple[str, UUID]] = set()

    def _tier(self) -> tuple[str, int]:
        if self.reservation_count >= 20:
            return "GOLD", 10
        if self.reservation_count >= 10:
            return "SILVER", 7
        return "BRONZE", 5

    async def get(self, username: str) -> LoyaltyData:
        self._calls.append("loyalty.get")
        status, discount = self._tier()
        return LoyaltyData(status=status, discount=discount, reservation_count=self.reservation_count)

    async def change_count(
        self, username: str, delta: int, operation_uid: UUID | None = None
    ) -> LoyaltyData:
        self._calls.append(f"loyalty.change_count({delta:+d})")
        if operation_uid is not None:
            key = (username, operation_uid)
            if key in self._operations:
                status, discount = self._tier()
                return LoyaltyData(
                    status=status, discount=discount, reservation_count=self.reservation_count
                )
            self._operations.add(key)
        self.reservation_count = max(0, self.reservation_count + delta)
        status, discount = self._tier()
        return LoyaltyData(status=status, discount=discount, reservation_count=self.reservation_count)
