from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.eventmaster_common import Role, Settings, has_permission

settings = Settings(service_name="notification-service", service_port=8407)
app = FastAPI(title="EventMaster Notification Service", version="1.0.0")

messages: list[dict[str, Any]] = []


class NotificationRequest(BaseModel):
    channel: str = "email"
    recipient: str
    subject: str
    body: str
    actor_role: Role
    async_mode: bool = False


class TicketNotificationRequest(BaseModel):
    user_id: str
    recipient: str
    event_id: str
    tickets: list[dict[str, Any]]
    actor_role: Role


class BulkNotificationRequest(BaseModel):
    event_id: str
    recipients: list[str]
    subject: str
    body: str
    channel: str = "email"
    actor_role: Role


NotificationRequest.model_rebuild()
TicketNotificationRequest.model_rebuild()
BulkNotificationRequest.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/notify/send")
async def send_notification(request: NotificationRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "notification:send")
    payload = {
        "message_id": str(uuid4()),
        "channel": request.channel,
        "recipient": request.recipient,
        "subject": request.subject,
        "body": request.body,
        "status": "queued" if request.async_mode else "sent",
    }
    messages.append(payload)
    return payload


@app.post("/notify/ticket")
async def send_ticket(request: TicketNotificationRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "notification:send")
    payload = {
        "message_id": str(uuid4()),
        "channel": "email",
        "recipient": request.recipient,
        "subject": f"Your tickets for {request.event_id}",
        "body": f"Generated {len(request.tickets)} e-ticket(s).",
        "status": "sent",
        "tickets": request.tickets,
    }
    messages.append(payload)
    return payload


@app.post("/notify/bulk")
async def send_bulk(request: BulkNotificationRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "notification:send")
    batch = []
    for recipient in request.recipients:
        item = {
            "message_id": str(uuid4()),
            "event_id": request.event_id,
            "channel": request.channel,
            "recipient": recipient,
            "subject": request.subject,
            "body": request.body,
            "status": "sent",
        }
        messages.append(item)
        batch.append(item)
    return {"event_id": request.event_id, "sent": len(batch), "items": batch}


@app.get("/notify/history")
async def history(channel: str | None = None) -> dict[str, Any]:
    items = [item for item in messages if not channel or item["channel"] == channel]
    return {"items": items, "count": len(items)}
