"""Клиенты соседних сервисов.

Для каждого сервиса объявлен абстрактный интерфейс и его HTTP-реализация: в unit-тестах
Gateway интерфейсы подменяются фейками, поэтому оркестрация проверяется без сети.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date
from uuid import UUID

from common.http import ServiceClient
from common.schemas import CamelModel


class HotelData(CamelModel):
    hotel_uid: UUID
    name: str
    country: str
    city: str
    address: str
    stars: int | None = None
    price: int


class HotelPageData(CamelModel):
    page: int
    page_size: int
    total_elements: int
    items: list[HotelData]


class HotelInfoData(CamelModel):
    hotel_uid: UUID
    name: str
    full_address: str
    stars: int | None = None


class ReservationData(CamelModel):
    reservation_uid: UUID
    payment_uid: UUID
    hotel: HotelInfoData
    start_date: date
    end_date: date
    status: str


class PaymentData(CamelModel):
    payment_uid: UUID
    status: str
    price: int


class LoyaltyData(CamelModel):
    status: str
    discount: int
    reservation_count: int


class ReservationServiceClient(ABC):
    @abstractmethod
    async def list_hotels(self, page: int, size: int) -> HotelPageData: ...

    @abstractmethod
    async def get_hotel(self, hotel_uid: UUID) -> HotelData | None: ...

    @abstractmethod
    async def list_reservations(self, username: str) -> list[ReservationData]: ...

    @abstractmethod
    async def get_reservation(self, reservation_uid: UUID, username: str) -> ReservationData | None: ...

    @abstractmethod
    async def create_reservation(
        self,
        *,
        username: str,
        payment_uid: UUID,
        hotel_uid: UUID,
        start_date: date,
        end_date: date,
    ) -> ReservationData: ...

    @abstractmethod
    async def cancel_reservation(self, reservation_uid: UUID, username: str) -> ReservationData | None: ...


class PaymentServiceClient(ABC):
    @abstractmethod
    async def create(self, price: int) -> PaymentData: ...

    @abstractmethod
    async def list_by_uids(self, payment_uids: Sequence[UUID]) -> list[PaymentData]: ...

    @abstractmethod
    async def cancel(self, payment_uid: UUID) -> PaymentData | None: ...


class LoyaltyServiceClient(ABC):
    @abstractmethod
    async def get(self, username: str) -> LoyaltyData: ...

    @abstractmethod
    async def change_count(self, username: str, delta: int) -> LoyaltyData: ...


class HttpReservationServiceClient(ReservationServiceClient):
    def __init__(self, client: ServiceClient) -> None:
        self._client = client

    async def list_hotels(self, page: int, size: int) -> HotelPageData:
        response = await self._client.send("GET", "/api/v1/hotels", params={"page": page, "size": size})
        assert response is not None
        return HotelPageData.model_validate(response.json())

    async def get_hotel(self, hotel_uid: UUID) -> HotelData | None:
        response = await self._client.send("GET", f"/api/v1/hotels/{hotel_uid}", not_found_ok=True)
        return HotelData.model_validate(response.json()) if response is not None else None

    async def list_reservations(self, username: str) -> list[ReservationData]:
        response = await self._client.send("GET", "/api/v1/reservations", username=username)
        assert response is not None
        return [ReservationData.model_validate(item) for item in response.json()]

    async def get_reservation(self, reservation_uid: UUID, username: str) -> ReservationData | None:
        response = await self._client.send(
            "GET", f"/api/v1/reservations/{reservation_uid}", username=username, not_found_ok=True
        )
        return ReservationData.model_validate(response.json()) if response is not None else None

    async def create_reservation(
        self,
        *,
        username: str,
        payment_uid: UUID,
        hotel_uid: UUID,
        start_date: date,
        end_date: date,
    ) -> ReservationData:
        payload = {
            "username": username,
            "paymentUid": str(payment_uid),
            "hotelUid": str(hotel_uid),
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
        }
        response = await self._client.send("POST", "/api/v1/reservations", json=payload)
        assert response is not None
        return ReservationData.model_validate(response.json())

    async def cancel_reservation(self, reservation_uid: UUID, username: str) -> ReservationData | None:
        response = await self._client.send(
            "POST",
            f"/api/v1/reservations/{reservation_uid}/cancel",
            username=username,
            not_found_ok=True,
        )
        return ReservationData.model_validate(response.json()) if response is not None else None


class HttpPaymentServiceClient(PaymentServiceClient):
    def __init__(self, client: ServiceClient) -> None:
        self._client = client

    async def create(self, price: int) -> PaymentData:
        response = await self._client.send("POST", "/api/v1/payments", json={"price": price})
        assert response is not None
        return PaymentData.model_validate(response.json())

    async def list_by_uids(self, payment_uids: Sequence[UUID]) -> list[PaymentData]:
        if not payment_uids:
            return []
        params = {"uids": [str(uid) for uid in payment_uids]}
        response = await self._client.send("GET", "/api/v1/payments", params=params)
        assert response is not None
        return [PaymentData.model_validate(item) for item in response.json()]

    async def cancel(self, payment_uid: UUID) -> PaymentData | None:
        response = await self._client.send(
            "POST", f"/api/v1/payments/{payment_uid}/cancel", not_found_ok=True
        )
        return PaymentData.model_validate(response.json()) if response is not None else None


class HttpLoyaltyServiceClient(LoyaltyServiceClient):
    def __init__(self, client: ServiceClient) -> None:
        self._client = client

    async def get(self, username: str) -> LoyaltyData:
        response = await self._client.send("GET", "/api/v1/loyalty", username=username)
        assert response is not None
        return LoyaltyData.model_validate(response.json())

    async def change_count(self, username: str, delta: int) -> LoyaltyData:
        response = await self._client.send(
            "PATCH", "/api/v1/loyalty", json={"delta": delta}, username=username
        )
        assert response is not None
        return LoyaltyData.model_validate(response.json())
