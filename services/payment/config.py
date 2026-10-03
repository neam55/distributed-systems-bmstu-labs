"""Настройки Payment Service."""

from functools import lru_cache

from common.config import DatabaseServiceSettings


class PaymentSettings(DatabaseServiceSettings):
    port: int = 8060
    database_url: str = "postgresql+asyncpg://program:test@localhost:5432/payments"


@lru_cache
def get_settings() -> PaymentSettings:
    return PaymentSettings()
