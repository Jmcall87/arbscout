from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Sequence

from . import db
from .models import Item, Opportunity, Quote, ScanSummary
from .normalization import compute_arbitrage, normalize_quote
from .valuation import build_valuation

_scan_lock = asyncio.Lock()


async def scan_once(
    settings: Any,
    venues: Sequence[Any],
    items: Sequence[Item],
    http: Any,
    browser: Any,
    fx: dict[str, Decimal] | None = None,
) -> ScanSummary:
    async with _scan_lock:
        return await _run_scan(settings, venues, items, http, browser, fx)


async def _run_scan(
    settings: Any,
    venues: Sequence[Any],
    items: Sequence[Item],
    http: Any,
    browser: Any,
    fx: dict[str, Decimal] | None,
) -> ScanSummary:
    summary = ScanSummary(venue_count=len(venues))
    for venue in venues:
        venue.clear_errors()

    tasks = [venue.fetch_quotes(items, http, browser) for venue in venues]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    collected: list[Quote] = []
    for venue, result in zip(venues, results):
        if isinstance(result, Exception):
            summary.errors.append(f"{venue.id}: {type(result).__name__}: {result}")
            continue
        collected.extend(result)
        summary.errors.extend(venue.errors)

    normalized = [normalize_quote(quote, items, fx) for quote in collected]
    normalized = [quote for quote in normalized if quote.price > 0 and quote.confidence > 0]
    db.insert_quotes(settings.db_path, normalized)
    summary.quote_count = len(normalized)

    valuations: dict[str, Any] = {}
    for item in items:
        history = db.get_quotes(settings.db_path, item.key, settings.history_limit)
        valuations[item.key] = build_valuation(item.key, history)

    latest: dict[tuple[str, str, str], Quote] = {}
    for quote in normalized:
        key = (quote.item_key, quote.venue, quote.side)
        previous = latest.get(key)
        if previous is None or quote.captured_at >= previous.captured_at:
            latest[key] = quote

    by_item: dict[str, list[Quote]] = {}
    for (item_key, _, _), quote in latest.items():
        by_item.setdefault(item_key, []).append(quote)

    opportunities: list[Opportunity] = []
    for item_key, quotes in by_item.items():
        valuation = valuations.get(item_key)
        buys = [quote for quote in quotes if quote.side == "buy"]
        sells = [quote for quote in quotes if quote.side == "sell"]

        for buy in buys:
            for sell in sells:
                if buy.venue == sell.venue or buy.currency != sell.currency:
                    continue
                maths = compute_arbitrage(buy, sell, settings.payment_spread_pct)
                if maths["net_profit"] <= 0:
                    continue
                confidence = min(buy.confidence, sell.confidence)
                if valuation is not None:
                    confidence *= valuation.confidence
                if confidence < settings.min_confidence:
                    continue
                if maths["net_profit"] < settings.min_net_profit:
                    continue
                if maths["roi_pct"] < settings.min_roi_pct:
                    continue

                flags: list[str] = []
                if (
                    valuation is not None
                    and valuation.fair_value is not None
                    and sell.price > valuation.fair_value * Decimal("1.5")
                ):
                    flags.append("sell quote is far above fair value")
                if sell.confidence < 0.5:
                    flags.append("low sell quote confidence")
                if len(quotes) < 4:
                    flags.append("thin cross-venue coverage")

                stamp = max(buy.captured_at, sell.captured_at)
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=timezone.utc)
                opportunity_id = str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        f"arbscout:{item_key}:{buy.venue}:{sell.venue}:{stamp.isoformat()}",
                    )
                )
                opportunities.append(
                    Opportunity(
                        id=opportunity_id,
                        item_key=item_key,
                        buy_venue=buy.venue,
                        buy_price=buy.price,
                        sell_venue=sell.venue,
                        sell_price=sell.price,
                        gross_spread=maths["gross_spread"],
                        buy_fee=maths["buy_fee"],
                        sell_fee=maths["sell_fee"],
                        payment_spread=maths["payment_spread"],
                        net_profit=maths["net_profit"],
                        roi_pct=maths["roi_pct"],
                        confidence=round(confidence, 4),
                        risk_flags=flags,
                        captured_at=stamp,
                    )
                )

    db.save_opportunities(settings.db_path, opportunities)
    summary.opportunity_count = len(opportunities)
    return summary
