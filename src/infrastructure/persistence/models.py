"""Отображение доменных сущностей на таблицы БД."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.domain.entities import Person


class Base(DeclarativeBase):
    """Базовый класс декларативных моделей."""


class PersonORM(Base):
    """Таблица persons."""

    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def to_domain(self) -> Person:
        """Сборка доменной сущности — БД наружу не протекает."""
        return Person(
            id=self.id,
            name=self.name,
            age=self.age,
            address=self.address,
            work=self.work,
        )
