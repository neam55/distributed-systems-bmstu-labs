"""Настройки Reservation Service."""

from functools import lru_cache

from common.config import DatabaseServiceSettings


class ReservationSettings(DatabaseServiceSettings):
    port: int = 8070
    database_url: str = "postgresql+asyncpg://program:test@localhost:5432/reservations"


@lru_cache
def get_settings() -> ReservationSettings:
    return ReservationSettings()
