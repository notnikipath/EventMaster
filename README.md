# EventMaster (Task 21)

EventMaster is a microservice platform for planning, promoting, and running events with ticket sales, attendee operations, sponsor management, and organizer analytics.

## Supported event types
- Conferences and forums
- Concerts and festivals
- Sports events
- Webinars and online courses
- Exhibitions

## Microservice structure
```text
eventmaster/
├── api-gateway/
├── event-service/
├── ticket-service/
├── payment-service/
├── attendee-service/
├── sponsor-service/
├── analytics-service/
├── notification-service/
├── shared/
├── frontend/
└── mobile-app/
```

## Core modules
- Event creation: description, date, venue, category, ticket type setup, promo codes.
- Ticket sales: seat selection, reservation, payment, e-ticket issuing (PDF URL + QR payload).
- Attendees: registration, check-in, mailing preparation, feedback.
- Sponsors: logo placement and contribution tracking.
- Analytics: sales, occupancy, demography, forecast, CSV export.

## Optional improvements implemented
- Group A: recommendations, dynamic pricing, attendance forecasting, feedback sentiment.
- Group B: messenger-friendly notifications (telegram channel), analytics export to CSV.
- Group C: gateway page cache, parallel booking plan, date sharding, async ticket generation.
- Group D: interactive seat map endpoint, mobile app starter.

## Tech stack
- Backend: FastAPI (Python)
- Data: PostgreSQL, Redis
- Queue: Celery (notification worker)
- Payments: Stripe-compatible mock flow in `payment-service`
- Frontend: React + Vite
- Mobile starter: React Native (Expo-ready skeleton)

## Run locally
```bash
cd d:\Шарага\Кинжа8\Task_21_EventMaster
docker compose up --build -d
```

## Key URLs
- Frontend: `http://localhost:5178`
- API Gateway: `http://localhost:8580`
- API docs: `http://localhost:8580/docs`

## Validation
```bash
python -m ruff check .
python -m pytest -q
docker compose config
```

## Demo workflow
```bash
python scripts/demo_pipeline.py
```

## Purchase workflow (gateway)
1. Ticket availability + reservation (`ticket-service`).
2. Payment processing (`payment-service`).
3. Ticket confirmation and async generation (`ticket-service`).
4. Ticket notification (`notification-service`).
5. Sales analytics update (`analytics-service`).

## Performance targets reflected in platform KPI
- Ticket purchase target: `< 3 sec`
- Throughput target: `1000 bookings/min`
- Scale target: `1,000,000 events`
