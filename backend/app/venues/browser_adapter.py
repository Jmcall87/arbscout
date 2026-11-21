from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Sequence
from urllib.parse import urlparse

from ..models import Item, Quote
from ..normalization import parse_money
from .base import VenueAdapter


class BrowserVenueAdapter(VenueAdapter):
    """
    Read-only scraper for publicly visible quote pages.

    Uses a transparent Playwright session. No stealth, CAPTCHA solving,
    fingerprint spoofing, or human-mimicry is implemented here by design.
    """

    kind = "browser"

    async def fetch_quotes(
        self,
        items: Sequence[Item],
        http: Any,
        browser: Any,
    ) -> list[Quote]:
        quotes: list[Quote] = []
        if browser is None or not getattr(browser, "available", False):
            self.errors.append(f"{self.id}: browser session unavailable")
            return quotes

        for page_cfg in self.config.get("pages", []):
            url = str(page_cfg.get("url", ""))
            if not url.startswith(("http://", "https://")):
                self.errors.append(f"{self.id}: invalid URL '{url}'")
                continue

            context = None
            try:
                allowed = await browser.allowed(url, http)
                if not allowed:
                    self.errors.append(f"{self.id}: robots.txt disallows {url}")
                    continue

                timeout_ms = int(page_cfg.get("timeout_ms", 15000))
                domain = urlparse(url).netloc
                await browser.acquire(domain, self.min_request_interval)

                context, page = await browser.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

                selector = str(page_cfg.get("wait_for_selector") or "")
                if selector:
                    await page.wait_for_selector(selector, timeout=timeout_ms)
                price_selector = str(page_cfg.get("price_selector", ""))
                if not price_selector:
                    self.errors.append(f"{self.id}: missing price_selector for {url}")
                    continue
                text = await page.text_content(price_selector, timeout=timeout_ms)

                price = parse_money(text)
                if price is None or price <= 0:
                    self.errors.append(f"{self.id}: no usable price at {url}")
                    continue

                try:
                    fee_pct = Decimal(str(page_cfg.get("fee_pct", 0)))
                except (InvalidOperation, ValueError):
                    fee_pct = Decimal("0")

                units = parse_money(page_cfg.get("units_per_lot", 1), Decimal("1"))
                units = units if units and units > 0 else Decimal("1")

                quotes.append(
                    Quote(
                        venue=self.id,
                        item_key=str(page_cfg.get("item_key", "unknown")),
                        side=str(page_cfg.get("side", "buy")),
                        price=price,
                        currency=str(page_cfg.get("currency", "USD")).upper(),
                        units_per_lot=units,
                        fee_pct=fee_pct,
                        source="browser",
                        confidence=float(page_cfg.get("confidence", 0.55)),
                        raw={"url": url, "selector": price_selector},
                    )
                )
            except Exception as exc:  # noqa: BLE001 - isolate per-page failures
                self.errors.append(f"{self.id}: {type(exc).__name__}: {exc}")
            finally:
                if context is not None:
                    try:
                        await context.close()
                    except Exception:
                        pass

        return quotes
