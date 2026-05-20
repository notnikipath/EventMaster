from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI

from shared.eventmaster_common import PaymentProcessRequest, PaymentStatus, PaymentTransaction, Settings

settings = Settings(service_name="payment-service", service_port=8403)
app = FastAPI(title="EventMaster Payment Service", version="1.0.0")

payments: dict[str, PaymentTransaction] = {}
orders_to_payment: dict[str, str] = {}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/payments/process")
async def process_payment(request: PaymentProcessRequest) -> dict[str, Any]:
    token = request.stripe_token or "tok_demo_success"
    failed = token.startswith("tok_fail")
    status = PaymentStatus.FAILED if failed else PaymentStatus.SUCCEEDED
    payment = PaymentTransaction(
        payment_id=str(uuid4()),
        order_id=request.order_id,
        user_id=request.user_id,
        amount_rub=request.amount_rub,
        provider=request.provider,
        status=status,
        transaction_ref=f"stripe_{uuid4().hex[:14]}",
        message="Payment declined by issuer" if failed else "Payment approved",
    )
    payments[payment.payment_id] = payment
    orders_to_payment[request.order_id] = payment.payment_id
    return payment.model_dump(mode="json")


@app.get("/payments/{payment_id}")
async def get_payment(payment_id: str) -> dict[str, Any]:
    payment = payments.get(payment_id)
    if payment is None:
        return {"status": "not_found", "payment_id": payment_id}
    return payment.model_dump(mode="json")


@app.get("/payments/order/{order_id}")
async def payment_by_order(order_id: str) -> dict[str, Any]:
    payment_id = orders_to_payment.get(order_id)
    if payment_id is None:
        return {"status": "not_found", "order_id": order_id}
    return payments[payment_id].model_dump(mode="json")
