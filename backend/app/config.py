from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
from typing import Any

VALID_MODES = ("research", "semi", "full")


def _bool(value: str | bool | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _int(value: str | int | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: str | float | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _decimal(value: str | Decimal | None, default: Decimal) -> Decimal:
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


@dataclass
class Settings:
    mode: str = "research"
    allowed_venues: set[str] = field(default_factory=set)
    max_spend_per_trade: Decimal = Decimal("50")
    max_spend_per_day: Decimal = Decimal("200")
    kill_switch: bool = True
    tos_ack: bool = False
    scan_interval_seconds: int = 300
    min_net_profit: Decimal = Decimal("0.50")
    min_roi_pct: Decimal = Decimal("0.5")
    min_confidence: float = 0.45
    payment_spread_pct: Decimal = Decimal("0")
    db_path: str = "/app/data/arbscout.db"
    history_limit: int = 200

    @classmethod
    def from_env(cls) -> "Settings":
        raw_venues = os.getenv("ARBSCOUT_ALLOWED_VENUES", "")
        mode = os.getenv("ARBSCOUT_MODE", "research").strip().lower()
        if mode not in VALID_MODES:
            mode = "research"
        return cls(
            mode=mode,
            allowed_venues={v.strip() for v in raw_venues.split(",") if v.strip()},
            max_spend_per_trade=_decimal(
                os.getenv("ARBSCOUT_MAX_SPEND_PER_TRADE"), Decimal("50")
            ),
            max_spend_per_day=_decimal(
                os.getenv("ARBSCOUT_MAX_SPEND_PER_DAY"), Decimal("200")
            ),
            kill_switch=_bool(os.getenv("ARBSCOUT_KILL_SWITCH"), True),
            tos_ack=_bool(os.getenv("ARBSCOUT_TOS_ACK"), False),
            scan_interval_seconds=_int(os.getenv("ARBSCOUT_SCAN_INTERVAL_SECONDS"), 300),
            min_net_profit=_decimal(os.getenv("ARBSCOUT_MIN_NET_PROFIT"), Decimal("0.50")),
            min_roi_pct=_decimal(os.getenv("ARBSCOUT_MIN_ROI_PCT"), Decimal("0.5")),
            min_confidence=_float(os.getenv("ARBSCOUT_MIN_CONFIDENCE"), 0.45),
            payment_spread_pct=_decimal(os.getenv("ARBSCOUT_PAYMENT_SPREAD_PCT"), Decimal("0")),
            db_path=os.getenv("ARBSCOUT_DB_PATH", "/app/data/arbscout.db"),
            history_limit=_int(os.getenv("ARBSCOUT_HISTORY_LIMIT"), 200),
        )

    def apply_overrides(self, overrides: dict[str, str]) -> "Settings":
        """Return a copy with persisted settings applied over environment defaults."""
        out = replace(self, allowed_venues=set(self.allowed_venues))
        for key, value in overrides.items():
            text = str(value)
            if key == "mode":
                if text in VALID_MODES:
                    out.mode = text
            elif key == "allowed_venues":
                out.allowed_venues = {v.strip() for v in text.split(",") if v.strip()}
            elif key == "kill_switch":
                out.kill_switch = _bool(text, self.kill_switch)
            elif key == "tos_ack":
                out.tos_ack = _bool(text, self.tos_ack)
            elif key == "max_spend_per_trade":
                out.max_spend_per_trade = _decimal(text, self.max_spend_per_trade)
            elif key == "max_spend_per_day":
                out.max_spend_per_day = _decimal(text, self.max_spend_per_day)
            elif key == "scan_interval_seconds":
                out.scan_interval_seconds = _int(text, self.scan_interval_seconds)
            elif key == "min_net_profit":
                out.min_net_profit = _decimal(text, self.min_net_profit)
            elif key == "min_roi_pct":
                out.min_roi_pct = _decimal(text, self.min_roi_pct)
            elif key == "min_confidence":
                out.min_confidence = _float(text, self.min_confidence)
            elif key == "payment_spread_pct":
                out.payment_spread_pct = _decimal(text, self.payment_spread_pct)
        return out

    def snapshot(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "allowed_venues": sorted(self.allowed_venues),
            "max_spend_per_trade": str(self.max_spend_per_trade),
            "max_spend_per_day": str(self.max_spend_per_day),
            "kill_switch": self.kill_switch,
            "tos_ack": self.tos_ack,
            "scan_interval_seconds": self.scan_interval_seconds,
            "min_net_profit": str(self.min_net_profit),
            "min_roi_pct": str(self.min_roi_pct),
            "min_confidence": self.min_confidence,
            "payment_spread_pct": str(self.payment_spread_pct),
        }
