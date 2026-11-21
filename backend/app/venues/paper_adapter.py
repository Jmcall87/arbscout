from __future__ import annotations

import time
import uuid
import zlib
from decimal import Decimal
from typing import Any, Sequence

from ..models import Item, Quote
from ..normalization import parse_money
from .base import VenueAdapter


class PaperVenueAdapter(VenueAdapter):
    """
    Deterministic simulated venue for end-to-end testing.

    It produces realistic buy/sell quotes and implements execution with fake
    order references. No network calls and no real money are involved. Every
    quote and order is tagged `simulated: true` so it can never be mistaken
    for a live venue.
    """

    kind = "paper"

    def _factor(self, label: str) -> Decimal:
        jitter = Decimal(str(self.config.get("jitter_pct", 0)))
        if jitter <= 0:
            return Decimal("1")
        bucket = int(time.time() // 60)
        digest = zlib.crc32(f"{self.id}:{label}:{bucket}".encode("utf-8")) / 0xFFFFFFFF
        offset = (Decimal(str(digest)) - Decimal("0.5")) * Decimal("2")
        return Decimal("1") + (jitter / Decimal("100")) * offset

    async def fetch_quotes(
        self,
        items: Sequence[Item],
        http: Any,
        browser: Any,
    ) -> list[Quote]:
        quotes: list[Quote] = []
        item_key = str(self.config.get("item_key", "demo:gold"))
        currency = str(self.config.get("currency", "USD")).upper()
        units = parse_money(self.config.get("units_per_lot", 1), Decimal("1")) or Decimal("1")
        fee_pct = parse_money(self.config.get("fee_pct", 0), Decimal("0")) or Decimal("0")

        for side in ("buy", "sell"):
            base = parse_money(self.config.get(f"{side}_price"))
            if base is None or base <= 0:
                continue
            quotes.append(
                Quote(
                    venue=self.id,
                    item_key=item_key,
                    side=side,
                    price=base * self._factor(side),
                    currency=currency,
                    units_per_lot=units,
                    fee_pct=fee_pct,
                    source="api",
                    confidence=0.85,
                    raw={"simulated": True},
                )
            )
        return quotes

    async def execute_buy(self, step: Any, http: Any, browser: Any) -> str:
        return f"PAPER-BUY-{uuid.uuid4().hex[:12]}"

    async def execute_sell(self, step: Any, http: Any, browser: Any) -> str:
        return f"PAPER-SELL-{uuid.uuid4().hex[:12]}"
