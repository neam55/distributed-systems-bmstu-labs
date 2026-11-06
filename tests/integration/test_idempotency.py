"""Real PostgreSQL races in a disposable schema, never in the seeded service tables."""

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import date
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from loyalty.entities import Loyalty, LoyaltyStatus
from loyalty.models import Base as LoyaltyBase
from loyalty.repository import SQLAlchemyLoyaltyRepository
from payment.entities import Payment, PaymentStatus
from payment.models import Base as PaymentBase
from payment.repository import SQLAlchemyPaymentRepository
from reservation.models import Base as ReservationBase
from reservation.models import HotelORM, ReservationORM
from reservation.repository import SQLAlchemyReservationRepository

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    url = os.environ.get("INTEGRATION_DATABASE_URL")
    if not url:
        pytest.skip("INTEGRATION_DATABASE_URL must point to a disposable test database")
    schema = "lab03_test_" + uuid4().hex
    admin = create_async_engine(url)
    async with admin.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    isolated = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
    try:
        async with isolated.begin() as connection:
            for metadata in (PaymentBase.metadata, ReservationBase.metadata, LoyaltyBase.metadata):
                await connection.run_sync(metadata.create_all)
        yield isolated
    finally:
        await isolated.dispose()
        async with admin.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin.dispose()


async def test_payment_create_compensate_race(engine: AsyncEngine) -> None:
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    uid = uuid4()

    async def create() -> None:
        async with sessions() as session:
            await SQLAlchemyPaymentRepository(session).add(
                Payment(payment_uid=uid, status=PaymentStatus.PAID, price=100)
            )

    async def compensate() -> None:
        async with sessions() as session:
            await SQLAlchemyPaymentRepository(session).compensate(uid)

    await asyncio.gather(create(), compensate(), create())
    async with sessions() as session:
        payment = await SQLAlchemyPaymentRepository(session).get(uid)
        assert payment is not None and payment.status == PaymentStatus.CANCELED


async def test_reservation_create_compensate_race(engine: AsyncEngine) -> None:
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    uid, hotel_uid, payment_uid = uuid4(), uuid4(), uuid4()
    async with sessions() as session:
        session.add(
            HotelORM(
                hotel_uid=hotel_uid,
                name="Test",
                country="RU",
                city="Moscow",
                address="Test",
                stars=5,
                price=100,
            )
        )
        await session.commit()

    async def create() -> None:
        async with sessions() as session:
            await SQLAlchemyReservationRepository(session).add_reservation(
                reservation_uid=uid,
                username="race",
                payment_uid=payment_uid,
                hotel_uid=hotel_uid,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 2),
            )

    async def compensate() -> None:
        async with sessions() as session:
            await SQLAlchemyReservationRepository(session).compensate(uid, "race")

    await asyncio.gather(create(), compensate(), create())
    async with sessions() as session:
        reservation = await SQLAlchemyReservationRepository(session).get_reservation(uid, "race")
        assert reservation is None
        assert await SQLAlchemyReservationRepository(session).list_reservations("race") == []
        stored = (
            (await session.execute(select(ReservationORM).where(ReservationORM.reservation_uid == uid)))
            .unique()
            .scalar_one()
        )
        assert stored.status == "CANCELED"


async def test_loyalty_increment_reverse_race(engine: AsyncEngine) -> None:
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    uid = uuid4()
    async with sessions() as session:
        await SQLAlchemyLoyaltyRepository(session).add(
            Loyalty(username="race", reservation_count=25, status=LoyaltyStatus.GOLD, discount=10)
        )

    async def increment() -> None:
        async with sessions() as session:
            await SQLAlchemyLoyaltyRepository(session).change_count("race", 1, uid)

    async def reverse() -> None:
        async with sessions() as session:
            await SQLAlchemyLoyaltyRepository(session).reverse_increment("race", uid)

    await asyncio.gather(increment(), reverse(), increment(), reverse())
    async with sessions() as session:
        loyalty = await SQLAlchemyLoyaltyRepository(session).get("race")
        assert loyalty is not None and loyalty.reservation_count == 25
