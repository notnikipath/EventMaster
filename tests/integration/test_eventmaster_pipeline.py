from pathlib import Path
from urllib.parse import urlsplit

from fastapi import HTTPException
from fastapi.testclient import TestClient

from tests.integration.helpers import load_module

ROOT = Path(__file__).resolve().parents[2]

event_module = load_module("event_module", ROOT / "event-service" / "app" / "main.py")
ticket_module = load_module("ticket_module", ROOT / "ticket-service" / "app" / "main.py")
payment_module = load_module("payment_module", ROOT / "payment-service" / "app" / "main.py")
analytics_module = load_module("analytics_module", ROOT / "analytics-service" / "app" / "main.py")
notification_module = load_module("notification_module", ROOT / "notification-service" / "app" / "main.py")
attendee_module = load_module("attendee_module", ROOT / "attendee-service" / "app" / "main.py")
sponsor_module = load_module("sponsor_module", ROOT / "sponsor-service" / "app" / "main.py")
gateway_module = load_module("gateway_module", ROOT / "api-gateway" / "app" / "main.py")

event_client = TestClient(event_module.app)
ticket_client = TestClient(ticket_module.app)
payment_client = TestClient(payment_module.app)
analytics_client = TestClient(analytics_module.app)
notification_client = TestClient(notification_module.app)
attendee_client = TestClient(attendee_module.app)
sponsor_client = TestClient(sponsor_module.app)
gateway_client = TestClient(gateway_module.app)


def _route_request(url: str, method: str, payload: dict | None = None, params: dict | None = None) -> dict:
    parsed = urlsplit(url)
    path = parsed.path
    client_map = {
        "event-service": event_client,
        "ticket-service": ticket_client,
        "payment-service": payment_client,
        "analytics-service": analytics_client,
        "notification-service": notification_client,
        "attendee-service": attendee_client,
        "sponsor-service": sponsor_client,
    }
    for service, client in client_map.items():
        if service in parsed.netloc:
            response = client.request(method, path, json=payload, params=params)
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    raise RuntimeError(f"Unsupported service URL: {url}")


async def _fake_get_json(client, url: str, params: dict | None = None) -> dict:
    return _route_request(url, "GET", params=params)


async def _fake_post_json(client, url: str, payload: dict) -> dict:
    return _route_request(url, "POST", payload=payload)


# Monkeypatch network hops so services can collaborate in-process during integration tests.
ticket_module._get_json = _fake_get_json
ticket_module._post_json = _fake_post_json
gateway_module._get_json = _fake_get_json
gateway_module._post_json = _fake_post_json


def test_purchase_workflow_end_to_end() -> None:
    response = gateway_client.post(
        "/workflow/purchase-ticket",
        json={
            "user_id": "attendee-001",
            "event_id": "EV-CONCERT-001",
            "ticket_type_id": "REGULAR",
            "quantity": 1,
            "seats": [{"row": "A", "number": 12}],
            "promo_code": "ROCK10",
            "payment_method": "card",
            "stripe_token": "tok_demo_success",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["reservation"]["status"] == "paid"
    assert payload["payment"]["status"] == "succeeded"
    assert len(payload["tickets"]) == 1
    assert payload["analytics"]["sold_tickets"] >= 1
    assert payload["duration_ms"] > 0


def test_dashboard_aggregation_and_cache() -> None:
    first = gateway_client.get("/dashboard/EV-CONCERT-001")
    assert first.status_code == 200
    assert first.json()["cached"] is False

    second = gateway_client.get("/dashboard/EV-CONCERT-001")
    assert second.status_code == 200
    payload = second.json()
    assert payload["cached"] is True
    assert payload["event"]["event_id"] == "EV-CONCERT-001"
    assert "availability" in payload
