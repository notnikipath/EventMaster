from __future__ import annotations

import argparse
import json

import httpx


async def run_demo(gateway_url: str, event_id: str, ticket_type_id: str) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        purchase = await client.post(
            f"{gateway_url}/workflow/purchase-ticket",
            json={
                "user_id": "demo-user",
                "event_id": event_id,
                "ticket_type_id": ticket_type_id,
                "quantity": 1,
                "seats": [{"row": "B", "number": 7}],
                "promo_code": "ROCK10",
                "payment_method": "card",
                "stripe_token": "tok_demo_success",
            },
        )
        purchase.raise_for_status()

        dashboard = await client.get(f"{gateway_url}/dashboard/{event_id}")
        dashboard.raise_for_status()

    print("Purchase workflow result:")
    print(json.dumps(purchase.json(), ensure_ascii=False, indent=2))
    print("\nDashboard snapshot:")
    print(json.dumps(dashboard.json(), ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run EventMaster demo purchase workflow")
    parser.add_argument("--gateway", default="http://localhost:8580", help="API Gateway URL")
    parser.add_argument("--event", default="EV-CONCERT-001", help="Event ID")
    parser.add_argument("--ticket-type", default="REGULAR", help="Ticket type ID")
    return parser.parse_args()


if __name__ == "__main__":
    import asyncio

    args = parse_args()
    asyncio.run(run_demo(args.gateway, args.event, args.ticket_type))
