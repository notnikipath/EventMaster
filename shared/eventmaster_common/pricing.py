from __future__ import annotations


def dynamic_ticket_price(base_price: float, sold: int, quota: int, days_to_event: int) -> float:
    if quota <= 0:
        return round(base_price, 2)
    occupancy = min(max(sold / quota, 0.0), 1.0)
    demand_factor = 1.0 + max(0.0, occupancy - 0.6) * 0.8
    urgency_factor = 1.12 if days_to_event <= 3 else 1.0
    early_bird_factor = 0.9 if days_to_event >= 30 else 1.0
    return round(base_price * demand_factor * urgency_factor * early_bird_factor, 2)


def apply_discount(total_rub: float, discount_percent: float) -> tuple[float, float]:
    discount = round(total_rub * max(min(discount_percent, 90), 0) / 100, 2)
    final_total = round(max(total_rub - discount, 0), 2)
    return final_total, discount
