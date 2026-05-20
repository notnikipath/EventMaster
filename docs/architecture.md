# EventMaster Architecture

## Services
- `api-gateway`: orchestration and dashboard aggregation.
- `event-service`: event catalog, ticket inventories, promo codes, sharding by date.
- `ticket-service`: reservations, seat selection, async e-ticket generation.
- `payment-service`: Stripe-like payment processing.
- `attendee-service`: registration, check-in, mailing lists, feedback.
- `sponsor-service`: sponsor registry, logos, contributions.
- `analytics-service`: sales and occupancy analytics, forecasting, CSV export.
- `notification-service`: email/telegram style notification dispatch + Celery worker.

## Datastores and infra
- `PostgreSQL`: primary persistent store (prepared in compose).
- `Redis`: cache, broker for Celery, and low-latency primitives.
- `Celery`: asynchronous notification jobs.

## Reliability ideas
- Event page cache in gateway (`TTLCache`).
- Reservation expiry and seat release in ticket service.
- Date-based shard key (`YYYY-MM`) in event service.
