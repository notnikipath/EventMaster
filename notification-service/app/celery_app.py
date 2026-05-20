from __future__ import annotations

from celery import Celery

from shared.eventmaster_common import Settings

settings = Settings(service_name="notification-service")

celery_app = Celery(
    "eventmaster-notification",
    broker=settings.celery_broker_url,
    backend=settings.celery_broker_url,
)
celery_app.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"])
