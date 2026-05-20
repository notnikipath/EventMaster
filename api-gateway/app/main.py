from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.eventmaster_common import PurchaseWorkflowRequest, Role, Settings, TTLCache, sign_token, verify_token


class GatewaySettings(BaseSettings):
    service_name: str = "api-gateway"
    service_port: int = 8400

    event_service_url: str = Settings().event_service_url
    ticket_service_url: str = Settings().ticket_service_url
    payment_service_url: str = Settings().payment_service_url
    attendee_service_url: str = Settings().attendee_service_url
    sponsor_service_url: str = Settings().sponsor_service_url
    analytics_service_url: str = Settings().analytics_service_url
    notification_service_url: str = Settings().notification_service_url

    jwt_secret: str = Settings().jwt_secret
    token_exp_minutes: int = 240

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = GatewaySettings()
app = FastAPI(title="EventMaster API Gateway", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5177",
        "http://127.0.0.1:5177",
        "http://localhost:5178",
        "http://127.0.0.1:5178",
        "http://localhost:32033",
        "http://127.0.0.1:32033",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

page_cache: TTLCache[dict[str, Any]] = TTLCache(ttl_seconds=45)


class AuthRequest(BaseModel):
    user_id: str
    role: Role


AuthRequest.model_rebuild()
PurchaseWorkflowRequest.model_rebuild()


async def _post_json(client: httpx.AsyncClient, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(url, json=payload)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = await client.get(url, params=params)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


def _service_urls() -> dict[str, str]:
    return {
        "event": settings.event_service_url,
        "ticket": settings.ticket_service_url,
        "payment": settings.payment_service_url,
        "attendee": settings.attendee_service_url,
        "sponsor": settings.sponsor_service_url,
        "analytics": settings.analytics_service_url,
        "notification": settings.notification_service_url,
    }


def _auto_select_seats(quantity: int, occupied: set[str]) -> list[dict[str, Any]]:
    seats: list[dict[str, Any]] = []
    for row_index in range(26):
        row = chr(ord("A") + row_index)
        for number in range(1, 1001):
            label = f"{row}-{number}"
            if label in occupied:
                continue
            occupied.add(label)
            seats.append({"row": row, "number": number})
            if len(seats) == quantity:
                return seats
    raise HTTPException(status_code=409, detail="Not enough seats available for automatic assignment")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/auth/token")
async def issue_token(request: AuthRequest) -> dict[str, str]:
    token = sign_token(
        {"sub": request.user_id, "role": request.role.value},
        settings.jwt_secret,
        exp_minutes=settings.token_exp_minutes,
    )
    return {"access_token": token, "token_type": "Bearer"}


@app.post("/auth/verify")
async def verify_auth(token: str) -> dict[str, Any]:
    payload = verify_token(token, settings.jwt_secret)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


@app.get("/services/health")
async def services_health() -> dict[str, Any]:
    statuses: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, base_url in _service_urls().items():
            try:
                statuses[name] = await _get_json(client, f"{base_url}/health")
            except Exception as exc:
                statuses[name] = {"status": "error", "detail": str(exc)}
    return statuses


@app.post("/workflow/purchase-ticket")
async def purchase_ticket_workflow(request: PurchaseWorkflowRequest) -> dict[str, Any]:
    started = perf_counter()
    stage_timings_ms: list[int] = []
    event: dict[str, Any] | None = None

    async with httpx.AsyncClient(timeout=25.0) as client:
        reservation_payload = request.model_dump(mode="json")
        if not reservation_payload.get("seats"):
            event = await _get_json(client, f"{settings.event_service_url}/events/{request.event_id}")
            if event.get("seating_enabled"):
                seat_state = await _get_json(client, f"{settings.ticket_service_url}/seats/{request.event_id}")
                occupied = set(seat_state.get("occupied", []))
                reservation_payload["seats"] = _auto_select_seats(request.quantity, occupied)

        t0 = perf_counter()
        reservation = await _post_json(
            client,
            f"{settings.ticket_service_url}/reservations",
            reservation_payload,
        )
        stage_timings_ms.append(round((perf_counter() - t0) * 1000))

        t1 = perf_counter()
        payment = await _post_json(
            client,
            f"{settings.payment_service_url}/payments/process",
            {
                "order_id": reservation["reservation_id"],
                "user_id": request.user_id,
                "amount_rub": reservation["total_rub"],
                "payment_method": request.payment_method,
                "provider": "stripe",
                "stripe_token": request.stripe_token,
            },
        )
        stage_timings_ms.append(round((perf_counter() - t1) * 1000))

        if payment["status"] != "succeeded":
            await _post_json(
                client,
                f"{settings.ticket_service_url}/reservations/{reservation['reservation_id']}/cancel",
                {"actor_id": "SYSTEM", "actor_role": "admin"},
            )
            raise HTTPException(status_code=402, detail="Payment failed")

        t2 = perf_counter()
        confirmed = await _post_json(
            client,
            f"{settings.ticket_service_url}/reservations/{reservation['reservation_id']}/confirm",
            {
                "payment_id": payment["payment_id"],
                "actor_id": "SYSTEM",
                "actor_role": "admin",
            },
        )
        stage_timings_ms.append(round((perf_counter() - t2) * 1000))

        t3 = perf_counter()
        if event is None:
            event = await _get_json(client, f"{settings.event_service_url}/events/{request.event_id}")
        analytics = await _post_json(
            client,
            f"{settings.analytics_service_url}/analytics/ingest/sales",
            {
                "event_id": request.event_id,
                "quantity": request.quantity,
                "revenue_rub": reservation["total_rub"],
                "capacity": event["capacity"],
                "purchase_latency_ms": sum(stage_timings_ms),
            },
        )
        stage_timings_ms.append(round((perf_counter() - t3) * 1000))

        notification = await _post_json(
            client,
            f"{settings.notification_service_url}/notify/ticket",
            {
                "user_id": request.user_id,
                "recipient": f"{request.user_id}@mail.eventmaster.local",
                "event_id": request.event_id,
                "tickets": confirmed["tickets"],
                "actor_role": "organizer",
            },
        )

    duration_ms = round((perf_counter() - started) * 1000)
    page_cache.clear()
    return {
        "reservation": confirmed["reservation"],
        "payment": payment,
        "tickets": confirmed["tickets"],
        "analytics": analytics,
        "notifications": [notification],
        "duration_ms": duration_ms,
    }


@app.get("/dashboard/{event_id}")
async def dashboard(event_id: str, refresh: bool = False) -> dict[str, Any]:
    cache_key = f"dashboard:{event_id}"
    if not refresh:
        cached = page_cache.get(cache_key)
        if cached is not None:
            return {**cached, "cached": True}

    async with httpx.AsyncClient(timeout=20.0) as client:
        event_task = _get_json(client, f"{settings.event_service_url}/events/{event_id}")
        availability_task = _get_json(client, f"{settings.event_service_url}/events/{event_id}/availability")
        sponsor_task = _get_json(client, f"{settings.sponsor_service_url}/events/{event_id}/showcase")
        ticket_task = _get_json(client, f"{settings.ticket_service_url}/seats/{event_id}")
        feedback_task = _get_json(client, f"{settings.attendee_service_url}/feedback", params={"event_id": event_id})
        notifications_task = _get_json(client, f"{settings.notification_service_url}/notify/history")

        event, availability, sponsors, seats, feedback, notifications = await asyncio.gather(
            event_task,
            availability_task,
            sponsor_task,
            ticket_task,
            feedback_task,
            notifications_task,
        )

        try:
            report = await _get_json(client, f"{settings.analytics_service_url}/analytics/report/{event_id}")
        except HTTPException:
            report = {
                "event_id": event_id,
                "sales": {"tickets_sold": 0, "revenue_rub": 0, "occupancy_rate": 0},
                "demography": {"age_groups": {}, "cities": {}},
                "performance": {
                    "avg_purchase_seconds": 0,
                    "avg_purchase_ms": 0,
                    "purchase_target_seconds": Settings().ticket_purchase_target_seconds,
                },
            }

        recommendations = await _get_json(
            client,
            f"{settings.event_service_url}/recommendations",
            params={"interests": event.get("category", "")},
        )
        platform_kpi = await _get_json(
            client,
            f"{settings.analytics_service_url}/analytics/platform-kpi",
            params={"actor_role": "organizer"},
        )

    payload = {
        "event": event,
        "availability": availability,
        "sponsors": sponsors,
        "seats": seats,
        "feedback": feedback,
        "notifications": notifications,
        "analytics_report": report,
        "recommendations": recommendations,
        "platform_kpi": platform_kpi,
    }
    page_cache.set(cache_key, payload)
    return {**payload, "cached": False}


@app.post("/cache/flush")
async def flush_cache() -> dict[str, str]:
    page_cache.clear()
    return {"status": "cleared"}
