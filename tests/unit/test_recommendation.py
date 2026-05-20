from datetime import UTC, datetime, timedelta

from shared.eventmaster_common import (
    Event,
    EventType,
    SentimentLabel,
    detect_sentiment,
    forecast_attendance,
    recommend_events,
)


def test_sentiment_detector() -> None:
    assert detect_sentiment("Очень полезно и супер организовано") == SentimentLabel.POSITIVE
    assert detect_sentiment("Слишком дорого и скучно") == SentimentLabel.NEGATIVE


def test_forecast_attendance() -> None:
    projection, confidence = forecast_attendance(capacity=1000, sold=200, days_to_event=10)
    assert projection >= 200
    assert 0 <= confidence <= 1


def test_recommend_events() -> None:
    event = Event(
        event_id="EV-1",
        title="AI Conference",
        description="Deep learning and product sessions",
        category="education",
        event_type=EventType.CONFERENCE,
        start_at=datetime.now(UTC) + timedelta(days=5),
        end_at=datetime.now(UTC) + timedelta(days=5, hours=8),
        venue="Expo",
        city="Moscow",
        capacity=500,
        organizer_id="ORG-1",
        shard_key="2026-06",
    )
    recommendations = recommend_events(["learning", "ai"], [event], sales_weight={"EV-1": 300})
    assert recommendations == ["EV-1"]
