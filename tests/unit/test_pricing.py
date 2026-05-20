from shared.eventmaster_common import apply_discount, dynamic_ticket_price


def test_dynamic_price_growth_when_demand_high() -> None:
    low = dynamic_ticket_price(2000, sold=120, quota=1000, days_to_event=12)
    high = dynamic_ticket_price(2000, sold=900, quota=1000, days_to_event=2)
    assert high > low


def test_discount_application() -> None:
    total, discount = apply_discount(5000, 10)
    assert total == 4500
    assert discount == 500
