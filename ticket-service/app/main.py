from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.eventmaster_common import (
    Role,
    Settings,
    TicketIssue,
    TicketReservation,
    TicketReservationRequest,
    TicketStatus,
    apply_discount,
    booking_parallel_plan,
)

settings = Settings(service_name="ticket-service", service_port=8402)
app = FastAPI(title="EventMaster Ticket Service", version="1.0.0")

reservations: dict[str, TicketReservation] = {}
reservation_promos: dict[str, str] = {}
tickets_by_reservation: dict[str, list[TicketIssue]] = {}
seats_taken: dict[str, set[str]] = {}


class ReservationConfirmRequest(BaseModel):
    payment_id: str
    actor_id: str = "SYSTEM"
    actor_role: Role = Role.ADMIN


class ReservationCancelRequest(BaseModel):
    actor_id: str = "SYSTEM"
    actor_role: Role = Role.ADMIN


ReservationConfirmRequest.model_rebuild()
ReservationCancelRequest.model_rebuild()


async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = await client.get(url, params=params)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


async def _post_json(client: httpx.AsyncClient, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(url, json=payload)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


def _seat_label(row: str, number: int) -> str:
    return f"{row.upper()}-{number}"


def _is_expired(reservation: TicketReservation) -> bool:
    return reservation.expires_at < datetime.now(UTC)


def _release_seats(reservation: TicketReservation) -> None:
    if not reservation.seats:
        return
    event_seats = seats_taken.setdefault(reservation.event_id, set())
    for seat in reservation.seats:
        event_seats.discard(_seat_label(seat.row, seat.number))


def _cleanup_expired() -> None:
    for reservation in list(reservations.values()):
        if reservation.status != TicketStatus.RESERVED:
            continue
        if _is_expired(reservation):
            reservation.status = TicketStatus.CANCELLED
            _release_seats(reservation)


def _active_reserved_count(event_id: str, ticket_type_id: str) -> int:
    total = 0
    for reservation in reservations.values():
        if reservation.event_id != event_id or reservation.ticket_type_id != ticket_type_id:
            continue
        if reservation.status == TicketStatus.RESERVED and not _is_expired(reservation):
            total += reservation.quantity
    return total


async def _generate_single_ticket(
    reservation: TicketReservation,
    order_position: int,
    seat_label: str | None,
) -> TicketIssue:
    ticket_id = str(uuid4())
    qr_payload = json.dumps(
        {
            "ticket_id": ticket_id,
            "event_id": reservation.event_id,
            "reservation_id": reservation.reservation_id,
            "user_id": reservation.user_id,
            "seat": seat_label,
        },
        separators=(",", ":"),
    )
    await asyncio.sleep(0)
    return TicketIssue(
        ticket_id=ticket_id,
        reservation_id=reservation.reservation_id,
        event_id=reservation.event_id,
        user_id=reservation.user_id,
        seat_label=seat_label,
        qr_payload=qr_payload,
        pdf_url=f"https://cdn.eventmaster.local/tickets/{reservation.reservation_id}/{order_position}.pdf",
    )


async def _generate_tickets_async(reservation: TicketReservation) -> list[TicketIssue]:
    labels = [_seat_label(seat.row, seat.number) for seat in reservation.seats]
    if not labels:
        labels = [None] * reservation.quantity
    tasks = [
        _generate_single_ticket(reservation, index + 1, labels[index] if index < len(labels) else None)
        for index in range(reservation.quantity)
    ]
    return await asyncio.gather(*tasks)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/processing/parallel-plan")
async def parallel_plan(bookings_per_min: int = 1000) -> dict[str, int]:
    return booking_parallel_plan(bookings_per_min)


@app.get("/seats/{event_id}")
async def seats(event_id: str) -> dict[str, Any]:
    occupied = sorted(seats_taken.get(event_id, set()))
    return {"event_id": event_id, "occupied": occupied, "count": len(occupied)}


@app.post("/reservations")
async def create_reservation(request: TicketReservationRequest) -> dict[str, Any]:
    _cleanup_expired()
    reserved_labels: list[str] = []
    occupied: set[str] | None = None
    async with httpx.AsyncClient(timeout=15.0) as client:
        event = await _get_json(client, f"{settings.event_service_url}/events/{request.event_id}")
        ticket_types = event.get("ticket_types", [])
        ticket_type = next((item for item in ticket_types if item["ticket_type_id"] == request.ticket_type_id), None)
        if ticket_type is None:
            raise HTTPException(status_code=404, detail="Ticket type not found")

        reserved_pending = _active_reserved_count(request.event_id, request.ticket_type_id)
        if ticket_type["sold"] + reserved_pending + request.quantity > ticket_type["quota"]:
            raise HTTPException(status_code=409, detail="Tickets are sold out for selected type")

        if event.get("seating_enabled"):
            if len(request.seats) != request.quantity:
                raise HTTPException(status_code=400, detail="Seat count must match quantity")
            labels = [_seat_label(seat.row, seat.number) for seat in request.seats]
            if len(set(labels)) != len(labels):
                raise HTTPException(status_code=409, detail="Duplicate seats in reservation")
            occupied = seats_taken.setdefault(request.event_id, set())
            conflicts = [label for label in labels if label in occupied]
            if conflicts:
                raise HTTPException(status_code=409, detail=f"Seats unavailable: {', '.join(conflicts)}")
            occupied.update(labels)
            reserved_labels = labels

        try:
            price = await _get_json(
                client,
                f"{settings.event_service_url}/events/{request.event_id}/ticket-types/{request.ticket_type_id}/price",
            )
            unit_price = price["dynamic_price_rub"]
            subtotal = round(unit_price * request.quantity, 2)
            discount_percent = 0.0

            if request.promo_code:
                promo_validation = await _get_json(
                    client,
                    f"{settings.event_service_url}/events/{request.event_id}/promocodes/{request.promo_code}/validate",
                )
                if not promo_validation.get("valid", False):
                    raise HTTPException(status_code=409, detail="Promo code is invalid")
                discount_percent = float(promo_validation["discount_percent"])
        except Exception:
            if occupied is not None and reserved_labels:
                for label in reserved_labels:
                    occupied.discard(label)
            raise

    total, discount = apply_discount(subtotal, discount_percent)
    reservation = TicketReservation(
        reservation_id=str(uuid4()),
        user_id=request.user_id,
        event_id=request.event_id,
        ticket_type_id=request.ticket_type_id,
        quantity=request.quantity,
        seats=request.seats,
        unit_price_rub=unit_price,
        subtotal_rub=subtotal,
        discount_rub=discount,
        total_rub=total,
        status=TicketStatus.RESERVED,
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
    )
    reservations[reservation.reservation_id] = reservation
    if request.promo_code:
        reservation_promos[reservation.reservation_id] = request.promo_code
    return reservation.model_dump(mode="json")


@app.get("/reservations/{reservation_id}")
async def get_reservation(reservation_id: str) -> dict[str, Any]:
    reservation = reservations.get(reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if reservation.status == TicketStatus.RESERVED and _is_expired(reservation):
        reservation.status = TicketStatus.CANCELLED
        _release_seats(reservation)
    payload = reservation.model_dump(mode="json")
    payload["promo_code"] = reservation_promos.get(reservation_id)
    return payload


@app.post("/reservations/{reservation_id}/confirm")
async def confirm_reservation(reservation_id: str, request: ReservationConfirmRequest) -> dict[str, Any]:
    reservation = reservations.get(reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if reservation.status != TicketStatus.RESERVED:
        raise HTTPException(status_code=409, detail="Reservation cannot be confirmed")
    if _is_expired(reservation):
        reservation.status = TicketStatus.CANCELLED
        _release_seats(reservation)
        raise HTTPException(status_code=409, detail="Reservation expired")

    async with httpx.AsyncClient(timeout=15.0) as client:
        await _post_json(
            client,
            f"{settings.event_service_url}/events/{reservation.event_id}/ticket-types/{reservation.ticket_type_id}/allocate",
            {
                "quantity": reservation.quantity,
                "actor_id": request.actor_id,
                "actor_role": request.actor_role.value,
            },
        )
        promo = reservation_promos.get(reservation_id)
        if promo:
            await _post_json(
                client,
                f"{settings.event_service_url}/events/{reservation.event_id}/promocodes/{promo}/consume",
                {
                    "uses": 1,
                    "actor_id": request.actor_id,
                    "actor_role": request.actor_role.value,
                },
            )

    reservation.status = TicketStatus.PAID
    tickets = await _generate_tickets_async(reservation)
    tickets_by_reservation[reservation_id] = tickets
    return {
        "reservation": reservation.model_dump(mode="json"),
        "payment_id": request.payment_id,
        "tickets": [ticket.model_dump(mode="json") for ticket in tickets],
    }


@app.post("/reservations/{reservation_id}/cancel")
async def cancel_reservation(reservation_id: str, request: ReservationCancelRequest) -> dict[str, Any]:
    reservation = reservations.get(reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if reservation.status == TicketStatus.PAID:
        raise HTTPException(status_code=409, detail="Paid reservations cannot be cancelled here")
    reservation.status = TicketStatus.CANCELLED
    _release_seats(reservation)
    return {
        "status": "cancelled",
        "reservation_id": reservation_id,
        "actor_id": request.actor_id,
        "actor_role": request.actor_role.value,
    }


@app.get("/tickets/reservation/{reservation_id}")
async def reservation_tickets(reservation_id: str) -> dict[str, Any]:
    items = [ticket.model_dump(mode="json") for ticket in tickets_by_reservation.get(reservation_id, [])]
    return {"items": items, "count": len(items)}
