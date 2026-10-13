from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.eventmaster_common import (
    Event,
    EventCreateRequest,
    EventPromoCode,
    EventTicketType,
    EventType,
    Role,
    Settings,
    build_audit_event,
    dynamic_ticket_price,
    has_permission,
    recommend_events,
)

settings = Settings(service_name="event-service", service_port=8401)
app = FastAPI(title="EventMaster Event Service", version="1.0.0")

events: dict[str, Event] = {}
audit_log: list[dict[str, Any]] = []


class EventCreateCommand(BaseModel):
    payload: EventCreateRequest
    actor_id: str
    actor_role: Role


class InventoryUpdateRequest(BaseModel):
    quantity: int = Field(gt=0)
    actor_id: str
    actor_role: Role


class PromoConsumeRequest(BaseModel):
    uses: int = Field(default=1, gt=0)
    actor_id: str
    actor_role: Role


EventCreateCommand.model_rebuild()
InventoryUpdateRequest.model_rebuild()
PromoConsumeRequest.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _audit(actor_id: str, actor_role: Role, action: str, object_id: str, details: dict[str, Any] | None = None) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type="event",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


def _shard_key(start_at: datetime) -> str:
    return start_at.strftime("%Y-%m")


def _map_create_request(event_id: str, request: EventCreateRequest) -> Event:
    return Event(
        event_id=event_id,
        title=request.title,
        description=request.description,
        category=request.category,
        event_type=request.event_type,
        start_at=request.start_at,
        end_at=request.end_at,
        venue=request.venue,
        city=request.city,
        capacity=request.capacity,
        organizer_id=request.organizer_id,
        is_online=request.is_online,
        seating_enabled=request.seating_enabled,
        shard_key=_shard_key(request.start_at),
        ticket_types=[EventTicketType(**ticket.model_dump()) for ticket in request.ticket_types],
        promo_codes=[EventPromoCode(**promo.model_dump()) for promo in request.promo_codes],
    )


def _find_ticket_type(event: Event, ticket_type_id: str) -> EventTicketType:
    for ticket_type in event.ticket_types:
        if ticket_type.ticket_type_id == ticket_type_id:
            return ticket_type
    raise HTTPException(status_code=404, detail="Ticket type not found")


def _find_promo(event: Event, promo_code: str) -> EventPromoCode:
    for promo in event.promo_codes:
        if promo.code.lower() == promo_code.lower():
            return promo
    raise HTTPException(status_code=404, detail="Promo code not found")


def _seed_demo_events() -> None:
    concert = Event(
        event_id="EV-CONCERT-001",
        title="Moscow SoundFest",
        description="Open-air concert with 4 stages and interactive fan zones.",
        category="music",
        event_type=EventType.CONCERT,
        start_at=datetime.now(UTC) + timedelta(days=16),
        end_at=datetime.now(UTC) + timedelta(days=16, hours=8),
        venue="Luzhniki Arena",
        city="Moscow",
        capacity=18000,
        organizer_id="ORG-001",
        seating_enabled=True,
        shard_key=_shard_key(datetime.now(UTC) + timedelta(days=16)),
        ticket_types=[
            EventTicketType(ticket_type_id="REGULAR", name="Regular", price_rub=4200, quota=14000, sold=2450),
            EventTicketType(ticket_type_id="VIP", name="VIP", price_rub=11900, quota=3000, sold=890, vip=True),
            EventTicketType(
                ticket_type_id="EARLY_BIRD",
                name="Early Bird",
                price_rub=3300,
                quota=1000,
                sold=1000,
                early_bird=True,
            ),
        ],
        promo_codes=[
            EventPromoCode(code="ROCK10", discount_percent=10, max_usages=600, used_count=231),
            EventPromoCode(code="FAN5", discount_percent=5, max_usages=1500, used_count=480),
        ],
    )
    webinar = Event(
        event_id="EV-WEB-001",
        title="AI Product Bootcamp",
        description="Two-day webinar about AI product strategy and GTM for startups.",
        category="education",
        event_type=EventType.WEBINAR,
        start_at=datetime.now(UTC) + timedelta(days=24),
        end_at=datetime.now(UTC) + timedelta(days=25),
        venue="online",
        city="online",
        capacity=5000,
        organizer_id="ORG-002",
        is_online=True,
        seating_enabled=False,
        shard_key=_shard_key(datetime.now(UTC) + timedelta(days=24)),
        ticket_types=[
            EventTicketType(ticket_type_id="STANDARD", name="Standard", price_rub=3200, quota=4200, sold=960),
            EventTicketType(ticket_type_id="PRO", name="Pro", price_rub=7800, quota=800, sold=310, vip=True),
        ],
        promo_codes=[EventPromoCode(code="LEARN15", discount_percent=15, max_usages=800, used_count=205)],
    )
    events[concert.event_id] = concert
    events[webinar.event_id] = webinar


_seed_demo_events()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/event-types")
async def event_types() -> dict[str, list[str]]:
    return {"items": [item.value for item in EventType]}


@app.get("/events")
async def list_events(
    event_type: EventType | None = None,
    city: str | None = None,
    category: str | None = None,
    shard_key: str | None = None,
    upcoming_only: bool = True,
) -> dict[str, Any]:
    items = []
    now = datetime.now(UTC)
    for event in events.values():
        if event_type and event.event_type != event_type:
            continue
        if city and event.city.lower() != city.lower():
            continue
        if category and event.category.lower() != category.lower():
            continue
        if shard_key and event.shard_key != shard_key:
            continue
        if upcoming_only and event.start_at < now:
            continue
        items.append(event.model_dump(mode="json"))
    items.sort(key=lambda item: item["start_at"])
    return {"items": items, "count": len(items)}




@app.post("/events")
async def create_event(command: EventCreateCommand) -> dict[str, Any]:
    _assert_permission(command.actor_role, "event:create")
    if command.payload.end_at <= command.payload.start_at:
        raise HTTPException(status_code=400, detail="Event end datetime must be later than start datetime")
    event_id = str(uuid4())
    event = _map_create_request(event_id, command.payload)
    events[event_id] = event
    _audit(command.actor_id, command.actor_role, "event.create", event_id, {"title": command.payload.title})
    return event.model_dump(mode="json")


@app.get("/events/{event_id}/availability")
async def availability(event_id: str) -> dict[str, Any]:
    event = events.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    ticket_items = []
    sold_total = 0
    for ticket_type in event.ticket_types:
        remaining = max(ticket_type.quota - ticket_type.sold, 0)
        sold_total += ticket_type.sold
        ticket_items.append(
            {
                "ticket_type_id": ticket_type.ticket_type_id,
                "name": ticket_type.name,
                "sold": ticket_type.sold,
                "quota": ticket_type.quota,
                "remaining": remaining,
            }
        )
    return {
        "event_id": event_id,
        "capacity": event.capacity,
        "tickets": ticket_items,
        "sold_total": sold_total,
        "remaining_capacity": max(event.capacity - sold_total, 0),
    }


@app.get("/events/{event_id}/ticket-types/{ticket_type_id}/price")
async def current_price(event_id: str, ticket_type_id: str) -> dict[str, Any]:
    event = events.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    ticket_type = _find_ticket_type(event, ticket_type_id)
    days_to_event = max((event.start_at.date() - datetime.now(UTC).date()).days, 0)
    dynamic_price = dynamic_ticket_price(ticket_type.price_rub, ticket_type.sold, ticket_type.quota, days_to_event)
    return {
        "event_id": event_id,
        "ticket_type_id": ticket_type_id,
        "base_price_rub": ticket_type.price_rub,
        "dynamic_price_rub": dynamic_price,
        "days_to_event": days_to_event,
    }


@app.get("/events/{event_id}/promocodes/{promo_code}/validate")
async def validate_promo(event_id: str, promo_code: str) -> dict[str, Any]:
    event = events.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    promo = _find_promo(event, promo_code)
    is_expired = promo.expires_at is not None and promo.expires_at < datetime.now(UTC)
    remaining = max(promo.max_usages - promo.used_count, 0)
    valid = (not is_expired) and remaining > 0
    return {
        "event_id": event_id,
        "code": promo.code,
        "discount_percent": promo.discount_percent,
        "remaining_uses": remaining,
        "is_expired": is_expired,
        "valid": valid,
    }


@app.post("/events/{event_id}/promocodes/{promo_code}/consume")
async def consume_promo(event_id: str, promo_code: str, request: PromoConsumeRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "ticket:manage")
    event = events.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    promo = _find_promo(event, promo_code)
    if promo.expires_at is not None and promo.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=409, detail="Promo code expired")
    if promo.used_count + request.uses > promo.max_usages:
        raise HTTPException(status_code=409, detail="Promo code usage limit reached")
    promo.used_count += request.uses
    _audit(
        request.actor_id,
        request.actor_role,
        "event.promo.consume",
        event_id,
        {"code": promo.code, "uses": request.uses},
    )
    return {"status": "consumed", "code": promo.code, "used_count": promo.used_count}


@app.post("/events/{event_id}/ticket-types/{ticket_type_id}/allocate")
async def allocate_inventory(event_id: str, ticket_type_id: str, request: InventoryUpdateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "ticket:manage")
    event = events.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    ticket_type = _find_ticket_type(event, ticket_type_id)
    if ticket_type.sold + request.quantity > ticket_type.quota:
        raise HTTPException(status_code=409, detail="Ticket quota exceeded")
    ticket_type.sold += request.quantity
    _audit(
        request.actor_id,
        request.actor_role,
        "event.inventory.allocate",
        event_id,
        {"ticket_type_id": ticket_type_id, "quantity": request.quantity},
    )
    return ticket_type.model_dump(mode="json")


@app.post("/events/{event_id}/ticket-types/{ticket_type_id}/deallocate")
async def deallocate_inventory(event_id: str, ticket_type_id: str, request: InventoryUpdateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "ticket:manage")
    event = events.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    ticket_type = _find_ticket_type(event, ticket_type_id)
    ticket_type.sold = max(ticket_type.sold - request.quantity, 0)
    _audit(
        request.actor_id,
        request.actor_role,
        "event.inventory.deallocate",
        event_id,
        {"ticket_type_id": ticket_type_id, "quantity": request.quantity},
    )
    return ticket_type.model_dump(mode="json")


@app.get("/recommendations")
async def recommendations(interests: str = "") -> dict[str, Any]:
    interests_list = [item.strip() for item in interests.split(",") if item.strip()]
    sales_weight = {
        event.event_id: sum(ticket.sold for ticket in event.ticket_types)
        for event in events.values()
    }
    recommended_ids = recommend_events(interests_list, list(events.values()), sales_weight=sales_weight)
    return {"items": recommended_ids, "count": len(recommended_ids)}


@app.get("/events/shards")
async def shard_distribution() -> dict[str, Any]:
    shards: dict[str, int] = {}
    for event in events.values():
        shards[event.shard_key] = shards.get(event.shard_key, 0) + 1
    return {"items": shards, "count": len(shards)}


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}


@app.get("/events/{event_id}")
async def get_event(event_id: str, actor_role: Role = Role.ATTENDEE) -> dict[str, Any]:
    _assert_permission(actor_role, "event:read")
    event = events.get(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event.model_dump(mode="json")
