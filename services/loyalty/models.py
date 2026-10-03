"""ORM-модель таблицы loyalty."""

from sqlalchemy import Integer, String
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
