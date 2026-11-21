from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from .models import Item, Quote

_MONEY_RE = re.compile(r"[-+]?\d[\d,\s\u00a0\u202f]*(?:\.\d+)?")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def parse_money(value: Any, default: Decimal | None = None) -> Decimal | None:
    """Best-effort conversion of a scraped/API value into a Decimal."""
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return default
    text = str(value).strip()
    match = _MONEY_RE.search(text)
    if not match:
        return default
    token = match.group(0)
    for mark in (",", " ", "\u00a0", "\u202f"):
        token = token.replace(mark, "")
    try:
        return Decimal(token)
    except InvalidOperation:
        return default


def slug(value: str) -> str:
    return _NON_ALNUM_RE.sub(":", value.strip().lower()).strip(":") or "unknown"


def canonical_key(game: str, name: str) -> str:
    return f"{slug(game)}:{slug(name)}"


def resolve_item_key(raw_key: str, items: list[Item]) -> str:
    """Map a venue-specific name to a canonical item key when possible."""
    needle = str(raw_key).strip().lower()
    for item in items:
        if needle == item.key.lower() or needle == item.name.lower():
            return item.key
        for alias in item.aliases:
            if needle == alias.strip().lower():
                return item.key
    return raw_key


def convert_currency(
    price: Decimal, source: str, target: str, fx: dict[str, Decimal] | None = None
) -> tuple[Decimal, bool]:
    """Convert price using fx keys like 'USD_EUR' (1 USD = 0.92 EUR)."""
    source = source.upper()
    target = target.upper()
    if source == target:
        return price, True
    rates = fx or {}
    direct = rates.get(f"{source}_{target}")
    if direct is not None:
        return price * direct, True
    inverse = rates.get(f"{target}_{source}")
    if inverse is not None and inverse != 0:
        return price / inverse, True
    return price, False


def normalize_quote(
    quote: Quote,
    items: list[Item],
    fx: dict[str, Decimal] | None = None,
) -> Quote:
    """Resolve item identity, lot size, and currency into a comparable quote."""
    item_map = {item.key.lower(): item for item in items}
    key = resolve_item_key(quote.item_key, items)
    item = item_map.get(key.lower())
    price = quote.price
    extras: dict[str, Any] = dict(quote.raw or {})
    confidence = quote.confidence

    if item is not None:
        if quote.units_per_lot > 0 and item.lot_size != quote.units_per_lot:
            price = price * (item.lot_size / quote.units_per_lot)
            extras["lot_adjusted"] = True
        converted, ok = convert_currency(price, quote.currency, item.currency, fx)
        if ok:
            price = converted
            currency = item.currency
        else:
            extras["fx_missing"] = True
            confidence *= 0.4
            currency = quote.currency.upper()
    else:
        extras["unknown_item"] = True
        confidence *= 0.5
        currency = quote.currency.upper()

    if price <= 0:
        extras["non_positive_price"] = True
        confidence = 0.0

    return quote.model_copy(
        update={
            "item_key": key,
            "price": price,
            "currency": currency,
            "units_per_lot": item.lot_size if item else quote.units_per_lot,
            "raw": extras,
            "confidence": max(0.0, min(1.0, confidence)),
        }
    )


def fee_adjusted_price(price: Decimal, fee_pct: Decimal, side: str) -> Decimal:
    """Effective cost for a buy, or effective proceeds for a sell."""
    rate = fee_pct / Decimal("100")
    if side == "buy":
        return price * (Decimal("1") + rate)
    return price * (Decimal("1") - rate)


def compute_arbitrage(
    buy: Quote,
    sell: Quote,
    payment_spread_pct: Decimal = Decimal("0"),
) -> dict[str, Decimal]:
    """Compute gross and net spread for buy@one venue, sell@another."""
    buy_fee = buy.price * buy.fee_pct / Decimal("100")
    sell_fee = sell.price * sell.fee_pct / Decimal("100")
    payment_spread = (buy.price + sell.price) * payment_spread_pct / Decimal("200")
    gross = sell.price - buy.price
    net = gross - buy_fee - sell_fee - payment_spread
    base = buy.price + buy_fee
    roi = (net / base * Decimal("100")) if base > 0 else Decimal("0")
    return {
        "gross_spread": gross,
        "buy_fee": buy_fee,
        "sell_fee": sell_fee,
        "payment_spread": payment_spread,
        "net_profit": net,
        "roi_pct": roi,
    }
