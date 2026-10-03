"""Граф зависимостей Payment Service."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import Database
from payment.config import get_settings
from payment.repository import PaymentRepository, SQLAlchemyPaymentRepository
from payment.service import PaymentService

_settings = get_settings()
database = Database(_settings.database_url, echo=_settings.echo_sql)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with database.session_factory() as session:
        yield session


def get_payment_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PaymentRepository:
    """Единственная точка выбора реализации хранилища; в тестах подменяется."""
    return SQLAlchemyPaymentRepository(session)


def get_payment_service(
    repository: Annotated[PaymentRepository, Depends(get_payment_repository)],
) -> PaymentService:
    return PaymentService(repository)


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
