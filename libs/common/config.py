"""Настройки, общие для всех сервисов системы."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    """Базовые настройки сервиса. Порт переопределяется в каждом сервисе."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    port: int = 8080


class DatabaseServiceSettings(BaseServiceSettings):
    """Настройки сервиса, владеющего собственной логической базой."""

    database_url: str
    echo_sql: bool = False

    @field_validator("database_url")
    @classmethod
    def _use_async_driver(cls, value: str) -> str:
        """Приводит URL к асинхронному драйверу: окружение может задать обычный postgres://."""
        for prefix in ("postgresql+asyncpg://", "sqlite+aiosqlite://"):
            if value.startswith(prefix):
                return value
        for prefix in ("postgresql://", "postgres://"):
            if value.startswith(prefix):
                return "postgresql+asyncpg://" + value[len(prefix) :]
        return value

    @property
    def sync_database_url(self) -> str:
        return self.database_url.replace("+asyncpg", "").replace("+aiosqlite", "")
