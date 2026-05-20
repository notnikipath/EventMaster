from __future__ import annotations

import csv
import io
from statistics import mean
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from shared.eventmaster_common import (
    EventForecast,
    Role,
    SalesSnapshot,
    Settings,
    demographic_groups,
    forecast_attendance,
    has_permission,
    occupancy_rate,
    ticket_purchase_latency_seconds,
)

settings = Settings(service_name="analytics-service", service_port=8406)
app = FastAPI(title="EventMaster Analytics Service", version="1.0.0")

sales_state: dict[str, dict[str, Any]] = {}
demography_state: dict[str, dict[str, Any]] = {}


class SalesIngestRequest(BaseModel):
    event_id: str
    quantity: int = Field(gt=0)
    revenue_rub: float = Field(ge=0)
    capacity: int = Field(gt=0)
    purchase_latency_ms: int = Field(ge=0)


class DemographyIngestRequest(BaseModel):
    event_id: str
    ages: list[int] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)


SalesIngestRequest.model_rebuild()
DemographyIngestRequest.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/analytics/ingest/sales")
async def ingest_sales(request: SalesIngestRequest) -> dict[str, Any]:
    record = sales_state.setdefault(
        request.event_id,
        {"tickets_sold": 0, "revenue_rub": 0.0, "capacity": request.capacity, "latency_ms": []},
    )
    record["tickets_sold"] += request.quantity
    record["revenue_rub"] = round(record["revenue_rub"] + request.revenue_rub, 2)
    record["capacity"] = request.capacity
    record["latency_ms"].append(request.purchase_latency_ms)

    snapshot = SalesSnapshot(
        event_id=request.event_id,
        sold_tickets=record["tickets_sold"],
        revenue_rub=record["revenue_rub"],
        occupancy_rate=occupancy_rate(record["tickets_sold"], record["capacity"]),
    )
    return snapshot.model_dump(mode="json")


@app.post("/analytics/ingest/demography")
async def ingest_demography(request: DemographyIngestRequest) -> dict[str, Any]:
    record = demography_state.setdefault(request.event_id, {"ages": [], "cities": {}})
    record["ages"].extend(request.ages)
    for city in request.cities:
        record["cities"][city] = record["cities"].get(city, 0) + 1
    return {
        "event_id": request.event_id,
        "age_groups": demographic_groups(record["ages"]),
        "cities": record["cities"],
    }


@app.get("/analytics/sales/{event_id}")
async def sales(event_id: str) -> dict[str, Any]:
    record = sales_state.get(event_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Sales stats not found")
    return {
        "event_id": event_id,
        "sold_tickets": record["tickets_sold"],
        "revenue_rub": record["revenue_rub"],
        "occupancy_rate": occupancy_rate(record["tickets_sold"], record["capacity"]),
    }


@app.get("/analytics/forecast/{event_id}")
async def forecast(event_id: str, days_to_event: int = 14) -> dict[str, Any]:
    record = sales_state.get(event_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Sales stats not found")
    projection, confidence = forecast_attendance(record["capacity"], record["tickets_sold"], days_to_event)
    payload = EventForecast(event_id=event_id, forecast_attendance=projection, confidence=confidence)
    return payload.model_dump(mode="json")


@app.get("/analytics/report/{event_id}")
async def report(event_id: str) -> dict[str, Any]:
    record = sales_state.get(event_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Sales stats not found")
    demography = demography_state.get(event_id, {"ages": [], "cities": {}})
    latency_ms = record["latency_ms"]
    latency_sec = ticket_purchase_latency_seconds(latency_ms)
    return {
        "event_id": event_id,
        "sales": {
            "tickets_sold": record["tickets_sold"],
            "revenue_rub": record["revenue_rub"],
            "occupancy_rate": occupancy_rate(record["tickets_sold"], record["capacity"]),
        },
        "demography": {
            "age_groups": demographic_groups(demography["ages"]),
            "cities": demography["cities"],
        },
        "performance": {
            "avg_purchase_seconds": latency_sec,
            "avg_purchase_ms": round(mean(latency_ms), 2) if latency_ms else 0.0,
            "purchase_target_seconds": settings.ticket_purchase_target_seconds,
        },
    }


@app.get("/analytics/report/{event_id}/export/csv", response_class=PlainTextResponse)
async def export_report_csv(event_id: str) -> str:
    report_payload = await report(event_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["metric", "value"])
    writer.writerow(["event_id", event_id])
    writer.writerow(["tickets_sold", report_payload["sales"]["tickets_sold"]])
    writer.writerow(["revenue_rub", report_payload["sales"]["revenue_rub"]])
    writer.writerow(["occupancy_rate", report_payload["sales"]["occupancy_rate"]])
    writer.writerow(["avg_purchase_seconds", report_payload["performance"]["avg_purchase_seconds"]])
    for bucket, value in report_payload["demography"]["age_groups"].items():
        writer.writerow([f"age_group_{bucket}", value])
    return output.getvalue()


@app.get("/analytics/platform-kpi")
async def platform_kpi(actor_role: Role = Role.ORGANIZER) -> dict[str, Any]:
    _assert_permission(actor_role, "analytics:read")
    latencies = [value for record in sales_state.values() for value in record["latency_ms"]]
    avg_purchase_seconds = ticket_purchase_latency_seconds(latencies)
    capacity_supported = settings.max_events_supported
    current_events = len(sales_state)
    estimated_throughput = min(
        settings.booking_throughput_target_per_min,
        300 + current_events * 8,
    )
    return {
        "ticket_purchase_target_seconds": settings.ticket_purchase_target_seconds,
        "current_avg_purchase_seconds": avg_purchase_seconds,
        "target_bookings_per_min": settings.booking_throughput_target_per_min,
        "estimated_bookings_per_min": estimated_throughput,
        "max_events_supported": capacity_supported,
    }
