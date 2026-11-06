"""Настройки Gateway Service."""

from functools import lru_cache

from pydantic import Field

from common.config import BaseServiceSettings


class GatewaySettings(BaseServiceSettings):
    """У Gateway нет своей базы: он только маршрутизирует и оркеструет вызовы."""

    port: int = 8080
    reservation_service_url: str = "http://localhost:8070"
    payment_service_url: str = "http://localhost:8060"
    loyalty_service_url: str = "http://localhost:8050"
    request_timeout: float = Field(default=2.0, gt=0)
    cb_failure_threshold: int = Field(default=3, gt=0)
    cb_recovery_timeout: float = Field(default=5.0, gt=0)
    retry_interval: float = Field(default=10.0, gt=0)


@lru_cache
def get_settings() -> GatewaySettings:
    return GatewaySettings()
