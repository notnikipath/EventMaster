from __future__ import annotations

from datetime import UTC, datetime

from .schemas import Event, SentimentLabel

POSITIVE_WORDS = {
    "great",
    "awesome",
    "excellent",
    "amazing",
    "удобно",
    "класс",
    "супер",
    "понрав",
    "полезно",
}
NEGATIVE_WORDS = {
    "bad",
    "boring",
    "awful",
    "terrible",
    "плохо",
    "скучно",
    "ужас",
    "долго",
    "дорого",
}


def recommend_events(
    user_interests: list[str],
    events: list[Event],
    sales_weight: dict[str, int] | None = None,
) -> list[str]:
    normalized = {interest.strip().lower() for interest in user_interests if interest.strip()}
    weighted_sales = sales_weight or {}
    scored: list[tuple[float, str]] = []
    now = datetime.now(UTC)

    for event in events:
        if event.start_at < now:
            continue
        event_text = f"{event.category} {event.title} {event.description}".lower()
        interest_hits = sum(1 for interest in normalized if interest in event_text)
        popularity = weighted_sales.get(event.event_id, 0) / 100
        score = interest_hits * 2.5 + popularity
        scored.append((score, event.event_id))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [event_id for _, event_id in scored[:5]]


def forecast_attendance(capacity: int, sold: int, days_to_event: int, daily_growth: float = 0.02) -> tuple[int, float]:
    if days_to_event <= 0:
        return min(capacity, sold), 0.95
    projected = sold
    for _ in range(days_to_event):
        projected += int(max(projected * daily_growth, 1))
    forecast = min(capacity, projected)
    confidence = 0.9 if days_to_event <= 14 else 0.75
    return forecast, confidence


def detect_sentiment(comment: str) -> SentimentLabel:
    text = comment.lower()
    positive_hits = sum(1 for word in POSITIVE_WORDS if word in text)
    negative_hits = sum(1 for word in NEGATIVE_WORDS if word in text)
    if positive_hits > negative_hits:
        return SentimentLabel.POSITIVE
    if negative_hits > positive_hits:
        return SentimentLabel.NEGATIVE
    return SentimentLabel.NEUTRAL
