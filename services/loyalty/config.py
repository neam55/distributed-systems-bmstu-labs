"""Настройки Loyalty Service."""

from functools import lru_cache

from common.config import DatabaseServiceSettings


class LoyaltySettings(DatabaseServiceSettings):
    port: int = 8050
    database_url: str = "postgresql+asyncpg://program:test@localhost:5432/loyalties"


@lru_cache
def get_settings() -> LoyaltySettings:
    return LoyaltySettings()
