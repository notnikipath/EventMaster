from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "eventmaster-service"
    service_port: int = 8400
    environment: str = "dev"

    postgres_dsn: str = "postgresql+psycopg://eventmaster:eventmaster@postgres:5432/eventmaster"
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    stripe_secret_key: str = "sk_test_eventmaster_demo"

    jwt_secret: str = "eventmaster-dev-secret"
    encryption_key: str = "eventmaster-dev-encryption-key"

    ticket_purchase_target_seconds: float = 3.0
    booking_throughput_target_per_min: int = 1000
    max_events_supported: int = 1_000_000

    event_service_url: str = "http://event-service:8401"
    ticket_service_url: str = "http://ticket-service:8402"
    payment_service_url: str = "http://payment-service:8403"
    attendee_service_url: str = "http://attendee-service:8404"
    sponsor_service_url: str = "http://sponsor-service:8405"
    analytics_service_url: str = "http://analytics-service:8406"
    notification_service_url: str = "http://notification-service:8407"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
