from __future__ import annotations


def occupancy_rate(sold: int, capacity: int) -> float:
    if capacity <= 0:
        return 0.0
    return round(min(max(sold / capacity, 0.0), 1.0), 4)


def ticket_purchase_latency_seconds(stages_ms: list[int]) -> float:
    if not stages_ms:
        return 0.0
    return round(sum(stages_ms) / 1000, 3)


def booking_parallel_plan(bookings_per_min: int) -> dict[str, int]:
    workers = min(64, max(4, bookings_per_min // 120))
    batch = max(20, bookings_per_min // max(workers, 1))
    return {
        "workers": workers,
        "batch_size": batch,
        "target_bookings_per_min": bookings_per_min,
    }


def demographic_groups(ages: list[int]) -> dict[str, int]:
    groups = {"under_18": 0, "18_24": 0, "25_34": 0, "35_44": 0, "45_plus": 0}
    for age in ages:
        if age < 18:
            groups["under_18"] += 1
        elif age <= 24:
            groups["18_24"] += 1
        elif age <= 34:
            groups["25_34"] += 1
        elif age <= 44:
            groups["35_44"] += 1
        else:
            groups["45_plus"] += 1
    return groups
