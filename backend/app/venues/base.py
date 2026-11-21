from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence

from ..models import Item, Quote


class VenueAdapter(ABC):
    """Base class for read-only quote collection and optional execution."""

    kind = "base"

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.id = str(config.get("id", "unknown"))
        self.label = str(config.get("label", self.id))
        self.permits_automation = bool(config.get("permits_automation", False))
        self.simulated = bool(config.get("simulated", False))
        self.errors: list[str] = []
        self.min_request_interval = float(config.get("min_request_interval", 2.0))

    @abstractmethod
    async def fetch_quotes(
        self,
        items: Sequence[Item],
        http: Any,
        browser: Any,
    ) -> list[Quote]:
        """Return quotes collected from this venue."""
        raise NotImplementedError

    async def execute_buy(self, step: Any, http: Any, browser: Any) -> str:
        """Override only when an official, documented API permits automation."""
        raise NotImplementedError(f"Venue '{self.id}' does not implement buy execution")

    async def execute_sell(self, step: Any, http: Any, browser: Any) -> str:
        """Override only when an official, documented API permits automation."""
        raise NotImplementedError(f"Venue '{self.id}' does not implement sell execution")

    def clear_errors(self) -> None:
        self.errors = []
