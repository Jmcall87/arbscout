from __future__ import annotations

import math
from collections import defaultdict
from decimal import Decimal
from statistics import median
from typing import Sequence

from .models import Quote, Valuation, VenueStats
from .research.market import estimate_likely_price, robust_sigma


def build_valuation(item_key: str, quotes: Sequence[Quote], min_samples: int = 3) -> Valuation:
    """Aggregate quote history into a fair value and a likely sell-back estimate."""
    by_venue: dict[str, list[Quote]] = defaultdict(list)
    for quote in quotes:
        if quote.confidence > 0 and quote.price > 0:
            by_venue[quote.venue].append(quote)

    per_venue: list[VenueStats] = []
    mids: list[Decimal] = []
    sell_history: list[tuple[object, Decimal]] = []

    for venue, venue_quotes in sorted(by_venue.items()):
        buys = [q.price for q in venue_quotes if q.side == "buy"]
        sells = [q.price for q in venue_quotes if q.side == "sell"]
        buy_med = median(buys) if buys else None
        sell_med = median(sells) if sells else None
        if buy_med is not None and sell_med is not None:
            mid = (buy_med + sell_med) / Decimal("2")
        else:
            mid = buy_med or sell_med

        if mid is not None:
            mids.append(mid)
        sell_history.extend((q.captured_at, q.price) for q in venue_quotes if q.side == "sell")

        venue_confidence = min(1.0, 0.3 + 0.7 * (1.0 - math.exp(-len(venue_quotes) / 8.0)))
        per_venue.append(
            VenueStats(
                venue=venue,
                buy=buy_med,
                sell=sell_med,
                mid=mid,
                sample_count=len(venue_quotes),
                confidence=round(venue_confidence, 4),
            )
        )

    fair = median(mids) if mids else None
    estimate = estimate_likely_price(sell_history)  # type: ignore[arg-type]
    likely = estimate["estimated"]
    notes: list[str] = []

    venue_confidences = [stats.confidence for stats in per_venue]
    venue_confidence = (
        sum(venue_confidences) / len(venue_confidences) if venue_confidences else 0.0
    )
    confidence = float(estimate["confidence"]) * 0.6 + venue_confidence * 0.4

    if sell_history:
        prices = [float(price) for _, price in sell_history]  # type: ignore[misc]
        if prices:
            centre = median(prices)
            notes.append(f"robust spread ~{robust_sigma(prices) / max(abs(centre), 1e-9):.2%}")

    if len(quotes) < min_samples:
        confidence *= 0.5
        notes.append("limited history")

    return Valuation(
        item_key=item_key,
        fair_value=fair,
        likely_sell_price=likely if isinstance(likely, Decimal) else None,
        confidence=round(min(1.0, max(0.0, confidence)), 4),
        sample_count=len(quotes),
        volatility=float(estimate["volatility"]),
        trend_pct_per_day=float(estimate["trend_pct_per_day"]),
        per_venue=per_venue,
        notes=notes,
    )
