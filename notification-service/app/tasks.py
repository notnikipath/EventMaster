from __future__ import annotations

from .celery_app import celery_app


@celery_app.task(name="notification.send")
def send_notification_task(payload: dict) -> dict:
    return {"status": "queued", "payload": payload}
