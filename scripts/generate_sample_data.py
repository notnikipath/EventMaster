from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


def build_sample_events() -> list[dict]:
    now = datetime.now(UTC)
    return [
        {
            "event_id": "EV-CONF-001",
            "title": "Tech Leadership Forum",
            "event_type": "conference",
            "start_at": (now + timedelta(days=30)).isoformat(),
            "end_at": (now + timedelta(days=30, hours=8)).isoformat(),
            "city": "Moscow",
            "capacity": 2500,
            "ticket_types": [
                {"ticket_type_id": "STANDARD", "price_rub": 6500, "quota": 1800},
                {"ticket_type_id": "VIP", "price_rub": 16500, "quota": 300},
            ],
        },
        {
            "event_id": "EV-CONCERT-001",
            "title": "Moscow SoundFest",
            "event_type": "concert",
            "start_at": (now + timedelta(days=16)).isoformat(),
            "end_at": (now + timedelta(days=16, hours=8)).isoformat(),
            "city": "Moscow",
            "capacity": 18000,
            "ticket_types": [
                {"ticket_type_id": "REGULAR", "price_rub": 4200, "quota": 14000},
                {"ticket_type_id": "VIP", "price_rub": 11900, "quota": 3000},
            ],
        },
        {
            "event_id": "EV-WEB-001",
            "title": "AI Product Bootcamp",
            "event_type": "webinar",
            "start_at": (now + timedelta(days=24)).isoformat(),
            "end_at": (now + timedelta(days=25)).isoformat(),
            "city": "online",
            "capacity": 5000,
            "ticket_types": [
                {"ticket_type_id": "STANDARD", "price_rub": 3200, "quota": 4200},
                {"ticket_type_id": "PRO", "price_rub": 7800, "quota": 800},
            ],
        },
    ]


def main() -> None:
    output_dir = Path("data") / "samples"
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "events": build_sample_events(),
    }

    output_file = output_dir / "eventmaster_events.json"
    output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Sample data written to {output_file}")


if __name__ == "__main__":
    main()
