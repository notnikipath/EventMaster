from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    CONFERENCE = "conference"
    CONCERT = "concert"
    SPORTS = "sports"
    WEBINAR = "webinar"
    EXHIBITION = "exhibition"


class Role(str, Enum):
    ATTENDEE = "attendee"
    ORGANIZER = "organizer"
    VOLUNTEER = "volunteer"
    SPONSOR = "sponsor"
    ADMIN = "admin"


class TicketStatus(str, Enum):
    RESERVED = "reserved"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentProvider(str, Enum):
    STRIPE = "stripe"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class SponsorTier(str, Enum):
    GENERAL = "general"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class TicketTypeConfig(BaseModel):
    ticket_type_id: str
    name: str
    price_rub: float = Field(gt=0)
    quota: int = Field(gt=0)
    perks: list[str] = Field(default_factory=list)
    early_bird: bool = False
    vip: bool = False


class PromoCodeConfig(BaseModel):
    code: str
    discount_percent: float = Field(ge=0, le=90)
    max_usages: int = Field(gt=0)
    expires_at: datetime | None = None


class EventCreateRequest(BaseModel):
    title: str
    description: str
    category: str
    event_type: EventType
    start_at: datetime
    end_at: datetime
    venue: str
    city: str
    capacity: int = Field(gt=0)
    organizer_id: str
    is_online: bool = False
    seating_enabled: bool = False
    ticket_types: list[TicketTypeConfig] = Field(default_factory=list)
    promo_codes: list[PromoCodeConfig] = Field(default_factory=list)


class EventTicketType(TicketTypeConfig):
    sold: int = 0


class EventPromoCode(PromoCodeConfig):
    used_count: int = 0


class Event(BaseModel):
    event_id: str
    title: str
    description: str
    category: str
    event_type: EventType
    start_at: datetime
    end_at: datetime
    venue: str
    city: str
    capacity: int
    organizer_id: str
    is_online: bool = False
    seating_enabled: bool = False
    shard_key: str
    ticket_types: list[EventTicketType] = Field(default_factory=list)
    promo_codes: list[EventPromoCode] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SeatSelection(BaseModel):
    row: str
    number: int = Field(gt=0)


class TicketReservationRequest(BaseModel):
    user_id: str
    event_id: str
    ticket_type_id: str
    quantity: int = Field(gt=0, le=10)
    seats: list[SeatSelection] = Field(default_factory=list)
    promo_code: str | None = None


class TicketReservation(BaseModel):
    reservation_id: str
    user_id: str
    event_id: str
    ticket_type_id: str
    quantity: int
    seats: list[SeatSelection] = Field(default_factory=list)
    unit_price_rub: float = Field(ge=0)
    subtotal_rub: float = Field(ge=0)
    discount_rub: float = Field(ge=0)
    total_rub: float = Field(ge=0)
    status: TicketStatus = TicketStatus.RESERVED
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PaymentProcessRequest(BaseModel):
    order_id: str
    user_id: str
    amount_rub: float = Field(gt=0)
    payment_method: str = "card"
    provider: PaymentProvider = PaymentProvider.STRIPE
    stripe_token: str | None = None


class PaymentTransaction(BaseModel):
    payment_id: str
    order_id: str
    user_id: str
    amount_rub: float
    provider: PaymentProvider
    status: PaymentStatus
    transaction_ref: str
    message: str = ""
    processed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TicketIssue(BaseModel):
    ticket_id: str
    reservation_id: str
    event_id: str
    user_id: str
    seat_label: str | None = None
    qr_payload: str
    pdf_url: str
    issued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AttendeeRegistrationRequest(BaseModel):
    event_id: str
    user_id: str
    full_name: str
    email: str
    age: int = Field(ge=0, le=120)
    city: str
    gender: str | None = None
    interests: list[str] = Field(default_factory=list)


class AttendeeProfile(BaseModel):
    attendee_id: str
    event_id: str
    user_id: str
    full_name: str
    email: str
    age: int
    city: str
    gender: str | None = None
    interests: list[str] = Field(default_factory=list)
    checked_in_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CheckInRequest(BaseModel):
    attendee_id: str
    volunteer_id: str


class BulkMessageRequest(BaseModel):
    event_id: str
    subject: str
    body: str
    channel: str = "email"


class FeedbackCreateRequest(BaseModel):
    attendee_id: str
    event_id: str
    rating: int = Field(ge=1, le=5)
    comment: str


class FeedbackItem(BaseModel):
    feedback_id: str
    attendee_id: str
    event_id: str
    rating: int
    comment: str
    sentiment: SentimentLabel
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SponsorCreateRequest(BaseModel):
    event_id: str
    name: str
    tier: SponsorTier = SponsorTier.GENERAL
    logo_url: str
    contribution_rub: float = Field(ge=0)
    website_url: str | None = None
    contact_email: str | None = None


class SponsorRecord(BaseModel):
    sponsor_id: str
    event_id: str
    name: str
    tier: SponsorTier
    logo_url: str
    contribution_rub: float
    website_url: str | None = None
    contact_email: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SalesSnapshot(BaseModel):
    event_id: str
    sold_tickets: int
    revenue_rub: float
    occupancy_rate: float
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EventForecast(BaseModel):
    event_id: str
    forecast_attendance: int
    confidence: float = Field(ge=0, le=1)


class PurchaseWorkflowRequest(BaseModel):
    user_id: str
    event_id: str
    ticket_type_id: str
    quantity: int = Field(default=1, gt=0, le=10)
    seats: list[SeatSelection] = Field(default_factory=list)
    promo_code: str | None = None
    payment_method: str = "card"
    stripe_token: str | None = None


class PurchaseWorkflowResult(BaseModel):
    reservation: dict[str, Any]
    payment: dict[str, Any]
    tickets: list[dict[str, Any]]
    analytics: dict[str, Any]
    notifications: list[dict[str, Any]] = Field(default_factory=list)
    duration_ms: int = 0


class AuditEvent(BaseModel):
    event_id: str
    actor_id: str
    actor_role: Role | str
    action: str
    object_type: str
    object_id: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
