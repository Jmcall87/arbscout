from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Sequence

import httpx

from ..models import Item, Quote
from ..normalization import parse_money
from .base import VenueAdapter


def get_path(data: Any, path: str) -> Any:
    """Small dot-path reader that also understands list indices."""
    current = data
    for part in str(path).split("."):
        if not part:
            continue
        if isinstance(current, dict):
            if part not in current:
                return None
            current = current[part]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current


class ApiVenueAdapter(VenueAdapter):
    kind = "api"

    async def fetch_quotes(
        self,
        items: Sequence[Item],
        http: Any,
        browser: Any,
    ) -> list[Quote]:
        base_url = str(self.config.get("base_url", "")).rstrip("/")
        timeout = float(self.config.get("request_timeout", 10))
        headers = self.config.get("headers") or {}
        quotes: list[Quote] = []

        async with httpx.AsyncClient(
            timeout=timeout, headers=headers, follow_redirects=True
        ) as client:
            for endpoint in self.config.get("endpoints", []):
                try:
                    path = str(endpoint.get("path", ""))
                    url = path if path.startswith("http") else f"{base_url}/{path.lstrip('/')}"
                    response = await client.get(url)
                    response.raise_for_status()
                    payload = response.json()

                    raw_price = get_path(payload, str(endpoint.get("price_jsonpath", "")))
                    price = parse_money(raw_price)
                    if price is None or price <= 0:
                        self.errors.append(f"{self.id}: no usable price at {url}")
                        continue

                    currency_path = endpoint.get("currency_jsonpath")
                    if currency_path:
                        currency = str(get_path(payload, str(currency_path)) or "USD")
                    else:
                        currency = str(endpoint.get("currency", "USD"))

                    try:
                        fee_pct = Decimal(str(endpoint.get("fee_pct", 0)))
                    except (InvalidOperation, ValueError):
                        fee_pct = Decimal("0")

                    units = parse_money(endpoint.get("units_per_lot", 1), Decimal("1"))
                    units = units if units and units > 0 else Decimal("1")

                    quotes.append(
                        Quote(
                            venue=self.id,
                            item_key=str(endpoint.get("item_key", "unknown")),
                            side=str(endpoint.get("side", "buy")),
                            price=price,
                            currency=currency.upper(),
                            units_per_lot=units,
                            fee_pct=fee_pct,
                            source="api",
                            confidence=float(endpoint.get("confidence", 0.75)),
                            raw={"url": url},
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - adapter must isolate failures
                    self.errors.append(f"{self.id}: {type(exc).__name__}: {exc}")

        return quotes
