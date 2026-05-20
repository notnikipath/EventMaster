from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from shared.eventmaster_common import (
    AttendeeProfile,
    AttendeeRegistrationRequest,
    BulkMessageRequest,
    CheckInRequest,
    FeedbackCreateRequest,
    FeedbackItem,
    Role,
    Settings,
    build_audit_event,
    demographic_groups,
    detect_sentiment,
    has_permission,
)

settings = Settings(service_name="attendee-service", service_port=8404)
app = FastAPI(title="EventMaster Attendee Service", version="1.0.0")

attendees: dict[str, AttendeeProfile] = {}
feedback_items: list[FeedbackItem] = []
audit_log: list[dict[str, Any]] = []


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _audit(actor_id: str, actor_role: Role, action: str, object_id: str, details: dict[str, Any] | None = None) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type="attendee",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/attendees/register")
async def register_attendee(request: AttendeeRegistrationRequest) -> dict[str, Any]:
    attendee = AttendeeProfile(attendee_id=str(uuid4()), **request.model_dump())
    attendees[attendee.attendee_id] = attendee
    return attendee.model_dump(mode="json")


@app.get("/attendees/{attendee_id}")
async def get_attendee(attendee_id: str) -> dict[str, Any]:
    attendee = attendees.get(attendee_id)
    if attendee is None:
        raise HTTPException(status_code=404, detail="Attendee not found")
    return attendee.model_dump(mode="json")


@app.get("/attendees")
async def list_attendees(event_id: str | None = None) -> dict[str, Any]:
    items = []
    for attendee in attendees.values():
        if event_id and attendee.event_id != event_id:
            continue
        items.append(attendee.model_dump(mode="json"))
    return {"items": items, "count": len(items)}


@app.post("/attendees/checkin")
async def check_in(request: CheckInRequest) -> dict[str, Any]:
    attendee = attendees.get(request.attendee_id)
    if attendee is None:
        raise HTTPException(status_code=404, detail="Attendee not found")
    attendee.checked_in_at = attendee.checked_in_at or datetime.now(UTC)
    _audit(request.volunteer_id, Role.VOLUNTEER, "attendee.checkin", request.attendee_id)
    return attendee.model_dump(mode="json")


@app.post("/mailing/prepare")
async def prepare_mailing(request: BulkMessageRequest) -> dict[str, Any]:
    recipients = [
        attendee.email
        for attendee in attendees.values()
        if attendee.event_id == request.event_id
    ]
    return {
        "event_id": request.event_id,
        "channel": request.channel,
        "subject": request.subject,
        "body": request.body,
        "recipients": recipients,
        "count": len(recipients),
    }


@app.post("/feedback")
async def create_feedback(request: FeedbackCreateRequest) -> dict[str, Any]:
    attendee = attendees.get(request.attendee_id)
    if attendee is None:
        raise HTTPException(status_code=404, detail="Attendee not found")
    sentiment = detect_sentiment(request.comment)
    feedback = FeedbackItem(
        feedback_id=str(uuid4()),
        attendee_id=request.attendee_id,
        event_id=request.event_id,
        rating=request.rating,
        comment=request.comment,
        sentiment=sentiment,
    )
    feedback_items.append(feedback)
    return feedback.model_dump(mode="json")


@app.get("/feedback")
async def list_feedback(event_id: str | None = None) -> dict[str, Any]:
    items = [
        item.model_dump(mode="json")
        for item in feedback_items
        if not event_id or item.event_id == event_id
    ]
    return {"items": items, "count": len(items)}


@app.get("/demography/{event_id}")
async def demography(event_id: str) -> dict[str, Any]:
    event_attendees = [item for item in attendees.values() if item.event_id == event_id]
    ages = [item.age for item in event_attendees]
    cities: dict[str, int] = {}
    genders: dict[str, int] = {}
    for attendee in event_attendees:
        cities[attendee.city] = cities.get(attendee.city, 0) + 1
        if attendee.gender:
            genders[attendee.gender] = genders.get(attendee.gender, 0) + 1
    return {
        "event_id": event_id,
        "total": len(event_attendees),
        "age_groups": demographic_groups(ages),
        "cities": cities,
        "genders": genders,
    }


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}
