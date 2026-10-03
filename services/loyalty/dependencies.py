"""Граф зависимостей Loyalty Service."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import Database
from loyalty.config import get_settings
from loyalty.repository import LoyaltyRepository, SQLAlchemyLoyaltyRepository
from loyalty.service import LoyaltyService

_settings = get_settings()
database = Database(_settings.database_url, echo=_settings.echo_sql)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with database.session_factory() as session:
        yield session


def get_loyalty_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LoyaltyRepository:
    """Единственная точка выбора реализации хранилища; в тестах подменяется."""
    return SQLAlchemyLoyaltyRepository(session)


def get_loyalty_service(
    repository: Annotated[LoyaltyRepository, Depends(get_loyalty_repository)],
) -> LoyaltyService:
    return LoyaltyService(repository)


LoyaltyServiceDep = Annotated[LoyaltyService, Depends(get_loyalty_service)]
UserName = Annotated[str, Header(alias="X-User-Name", description="Имя пользователя")]
