"""ORM-модель таблицы loyalty."""

from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from loyalty.entities import Loyalty, LoyaltyStatus


class Base(DeclarativeBase):
    """Базовый класс декларативных моделей сервиса."""


class LoyaltyORM(Base):
    __tablename__ = "loyalty"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    reservation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(80), nullable=False, default=LoyaltyStatus.BRONZE.value)
    discount: Mapped[int] = mapped_column(Integer, nullable=False)

    def to_domain(self) -> Loyalty:
        return Loyalty(
            id=self.id,
            username=self.username,
            reservation_count=self.reservation_count,
            status=LoyaltyStatus(self.status),
            discount=self.discount,
        )


class LoyaltyOperationORM(Base):
    """Ключи уже применённых изменений счётчика, в одной транзакции с loyalty."""

    __tablename__ = "loyalty_operation"

    username: Mapped[str] = mapped_column(
        String(80), ForeignKey("loyalty.username"), primary_key=True
    )
    operation_uid: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
