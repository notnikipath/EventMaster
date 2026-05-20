# Optional Improvements Implemented

## Group A
1. Event recommendation engine (`event-service /recommendations`).
2. Dynamic ticket pricing (`event-service /events/{id}/ticket-types/{id}/price`).
3. Attendance forecasting (`analytics-service /analytics/forecast/{event_id}`).
4. Feedback sentiment detection (`attendee-service /feedback`).

## Group B
1. Messaging integration by channel (`notification-service /notify/send`, supports `telegram`).
2. Export analytics to spreadsheet-friendly format (`analytics-service /analytics/report/{event_id}/export/csv`).

## Group C
1. Event page caching in gateway (`/dashboard/{event_id}`).
2. Parallel booking plan endpoint (`ticket-service /processing/parallel-plan`).
3. Date-based event sharding (`event-service /events/shards`).
4. Async ticket generation (`ticket-service`, `asyncio.gather`).

## Group D
1. Interactive hall-seat base endpoint (`ticket-service /seats/{event_id}`).
2. Mobile app starter (`mobile-app/`).
