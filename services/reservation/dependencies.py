"""Граф зависимостей Reservation Service."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import Database
from reservation.config import get_settings
from reservation.repository import ReservationRepository, SQLAlchemyReservationRepository
from reservation.service import ReservationService

_settings = get_settings()
database = Database(_settings.database_url, echo=_settings.echo_sql)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with database.session_factory() as session:
        yield session


def get_reservation_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReservationRepository:
    """Единственная точка выбора реализации хранилища; в тестах подменяется."""
    return SQLAlchemyReservationRepository(session)


def get_reservation_service(
    repository: Annotated[ReservationRepository, Depends(get_reservation_repository)],
) -> ReservationService:
    return ReservationService(repository)


ReservationServiceDep = Annotated[ReservationService, Depends(get_reservation_service)]
UserName = Annotated[str, Header(alias="X-User-Name", description="Имя пользователя")]
