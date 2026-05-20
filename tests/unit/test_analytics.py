from shared.eventmaster_common import booking_parallel_plan, occupancy_rate, ticket_purchase_latency_seconds


def test_occupancy_rate() -> None:
    assert occupancy_rate(500, 1000) == 0.5


def test_purchase_latency_seconds() -> None:
    assert ticket_purchase_latency_seconds([1000, 700, 300]) == 2.0


def test_parallel_plan() -> None:
    plan = booking_parallel_plan(1200)
    assert plan["workers"] >= 4
    assert plan["batch_size"] >= 20
