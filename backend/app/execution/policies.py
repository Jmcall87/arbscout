from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from ..config import Settings


@dataclass
class PolicyResult:
    allowed: bool
    reason: str


class ExecutionPolicy:
    """All gates that must pass before any real-money action is attempted."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(self, venue: Any, amount: Decimal) -> PolicyResult:
        if self.settings.kill_switch:
            return PolicyResult(False, "kill switch is enabled")
        if self.settings.mode != "full":
            return PolicyResult(
                False, f"mode is '{self.settings.mode}', execution requires 'full'"
            )
        if venue.id not in self.settings.allowed_venues:
            return PolicyResult(False, f"venue '{venue.id}' is not allowlisted")
        if not venue.permits_automation:
            return PolicyResult(False, f"venue '{venue.id}' does not permit automation")
        if not self.settings.tos_ack:
            return PolicyResult(False, "terms acknowledgement is not set")
        if amount <= 0:
            return PolicyResult(False, "amount must be positive")
        if amount > self.settings.max_spend_per_trade:
            return PolicyResult(False, "amount exceeds per-trade spend cap")
        return PolicyResult(True, "all execution gates passed")
