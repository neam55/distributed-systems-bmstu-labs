"""ORM-модель таблицы payment."""

from uuid import UUID as PyUUID

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from payment.entities import Payment, PaymentStatus


class Base(DeclarativeBase):
    """Базовый класс декларативных моделей сервиса."""


class PaymentORM(Base):
    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payment_uid: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)

    def to_domain(self) -> Payment:
        return Payment(
            id=self.id,
            payment_uid=self.payment_uid,
            status=PaymentStatus(self.status),
            price=self.price,
        )
