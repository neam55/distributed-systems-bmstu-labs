"""Конфигурация приложения из переменных окружения."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки сервиса.

    database_url нормализуется под асинхронный драйвер: хостеры (Render, Heroku)
    отдают DATABASE_URL в виде postgres://… или postgresql://…, а SQLAlchemy
    с asyncpg ожидает postgresql+asyncpg://…
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://program:test@localhost:5432/persons"
    echo_sql: bool = False

    @field_validator("database_url")
    @classmethod
    def _use_async_driver(cls, value: str) -> str:
        for prefix in ("postgresql+asyncpg://", "sqlite+aiosqlite://"):
            if value.startswith(prefix):
                return value
        for prefix in ("postgresql://", "postgres://"):
            if value.startswith(prefix):
                return "postgresql+asyncpg://" + value[len(prefix) :]
        return value

    @property
    def sync_database_url(self) -> str:
        """URL для инструментов без поддержки async (при необходимости)."""
        return self.database_url.replace("+asyncpg", "").replace("+aiosqlite", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
