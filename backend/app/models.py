from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Item(BaseModel):
    key: str
    game: str = ""
    name: str = ""
    unit: str = ""
    lot_size: Decimal = Decimal("1")
    currency: str = "USD"
    aliases: list[str] = Field(default_factory=list)


class Quote(BaseModel):
    venue: str
    item_key: str
    side: Literal["buy", "sell"]
    price: Decimal
    currency: str = "USD"
    units_per_lot: Decimal = Decimal("1")
    fee_pct: Decimal = Decimal("0")
    captured_at: datetime = Field(default_factory=utcnow)
    source: Literal["api", "browser"] = "api"
    confidence: float = 0.6
    raw: dict[str, Any] | None = None


class VenueStats(BaseModel):
    venue: str
    buy: Decimal | None = None
    sell: Decimal | None = None
    mid: Decimal | None = None
    sample_count: int = 0
    confidence: float = 0.0


class Valuation(BaseModel):
    item_key: str
    fair_value: Decimal | None = None
    likely_sell_price: Decimal | None = None
    confidence: float = 0.0
    sample_count: int = 0
    volatility: float = 0.0
    trend_pct_per_day: float = 0.0
    per_venue: list[VenueStats] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utcnow)
    notes: list[str] = Field(default_factory=list)


class Opportunity(BaseModel):
    id: str
    item_key: str
    buy_venue: str
    buy_price: Decimal
    sell_venue: str
    sell_price: Decimal
    gross_spread: Decimal = Decimal("0")
    buy_fee: Decimal = Decimal("0")
    sell_fee: Decimal = Decimal("0")
    payment_spread: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")
    roi_pct: Decimal = Decimal("0")
    confidence: float = 0.0
    risk_flags: list[str] = Field(default_factory=list)
    captured_at: datetime = Field(default_factory=utcnow)


class PlanStep(BaseModel):
    action: Literal["buy", "sell"]
    venue: str
    item_key: str
    amount: Decimal
    currency: str = "USD"
    note: str = ""


class Plan(BaseModel):
    id: str
    opportunity_id: str
    mode: str
    steps: list[PlanStep]
    approval_required: bool = True
    approved: bool = False
    executed: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    reason: str = ""


class AuditEntry(BaseModel):
    id: int | None = None
    timestamp: datetime = Field(default_factory=utcnow)
    event: str
    detail: str = ""
    mode: str = "research"
    allowed: bool = True


class ScanSummary(BaseModel):
    scanned_at: datetime = Field(default_factory=utcnow)
    venue_count: int = 0
    quote_count: int = 0
    opportunity_count: int = 0
    errors: list[str] = Field(default_factory=list)
