from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.eventmaster_common import (
    Role,
    Settings,
    SponsorCreateRequest,
    SponsorRecord,
    build_audit_event,
    has_permission,
)

settings = Settings(service_name="sponsor-service", service_port=8405)
app = FastAPI(title="EventMaster Sponsor Service", version="1.0.0")

sponsors: dict[str, SponsorRecord] = {}
audit_log: list[dict[str, Any]] = []


class SponsorCommand(BaseModel):
    payload: SponsorCreateRequest
    actor_id: str
    actor_role: Role


SponsorCommand.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _audit(actor_id: str, actor_role: Role, action: str, object_id: str, details: dict[str, Any] | None = None) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type="sponsor",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


def _seed_sponsor() -> None:
    sponsor = SponsorRecord(
        sponsor_id="SP-001",
        event_id="EV-CONCERT-001",
        name="Aurora Audio",
        tier="gold",
        logo_url="https://cdn.eventmaster.local/logos/aurora-audio.png",
        contribution_rub=1_500_000,
        website_url="https://aurora-audio.example.com",
        contact_email="partner@aurora-audio.example.com",
    )
    sponsors[sponsor.sponsor_id] = sponsor


_seed_sponsor()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/sponsors")
async def create_sponsor(command: SponsorCommand) -> dict[str, Any]:
    _assert_permission(command.actor_role, "sponsor:manage")
    sponsor = SponsorRecord(sponsor_id=str(uuid4()), **command.payload.model_dump())
    sponsors[sponsor.sponsor_id] = sponsor
    _audit(command.actor_id, command.actor_role, "sponsor.create", sponsor.sponsor_id)
    return sponsor.model_dump(mode="json")


@app.get("/sponsors")
async def list_sponsors(event_id: str | None = None) -> dict[str, Any]:
    items = [
        sponsor.model_dump(mode="json")
        for sponsor in sponsors.values()
        if not event_id or sponsor.event_id == event_id
    ]
    return {"items": items, "count": len(items)}


@app.get("/events/{event_id}/showcase")
async def sponsor_showcase(event_id: str) -> dict[str, Any]:
    items = [sponsor.model_dump(mode="json") for sponsor in sponsors.values() if sponsor.event_id == event_id]
    total_contribution = round(sum(item["contribution_rub"] for item in items), 2)
    return {
        "event_id": event_id,
        "items": items,
        "count": len(items),
        "total_contribution_rub": total_contribution,
    }


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}
