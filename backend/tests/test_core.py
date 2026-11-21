import asyncio
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from app import db
from app.config import Settings
from app.execution.policies import ExecutionPolicy
from app.models import Item, Quote
from app.normalization import compute_arbitrage, parse_money, resolve_item_key
from app.research.market import estimate_likely_price
from app.scanner import scan_once
from app.venues.paper_adapter import PaperVenueAdapter
from app.venues.registry import load_items, load_venues


class TestNormalization(unittest.TestCase):
    def test_parse_money(self):
        self.assertEqual(parse_money("$1,234.56"), Decimal("1234.56"))
        self.assertEqual(parse_money("96.40 USD"), Decimal("96.40"))
        self.assertIsNone(parse_money("n/a"))

    def test_resolve_alias(self):
        items = [Item(key="demo:gold", name="Gold", aliases=["gold coins"])]
        self.assertEqual(resolve_item_key("Gold Coins", items), "demo:gold")
        self.assertEqual(resolve_item_key("mystery", items), "mystery")

    def test_arbitrage_math(self):
        buy = Quote(venue="a", item_key="x", side="buy", price=Decimal("100"), fee_pct=Decimal("1"))
        sell = Quote(venue="b", item_key="x", side="sell", price=Decimal("110"), fee_pct=Decimal("2"))
        result = compute_arbitrage(buy, sell)
        self.assertEqual(result["gross_spread"], Decimal("10"))
        self.assertEqual(result["buy_fee"], Decimal("1"))
        self.assertEqual(result["sell_fee"], Decimal("2.20"))
        self.assertEqual(result["net_profit"], Decimal("6.80"))


class TestMarket(unittest.TestCase):
    def test_estimate_with_flat_history(self):
        now = datetime.now(timezone.utc)
        observations = [(now - timedelta(hours=i), Decimal("100")) for i in range(10)]
        result = estimate_likely_price(observations)
        self.assertEqual(result["estimated"], Decimal("100.000000"))
        self.assertGreater(result["confidence"], 0.4)

    def test_empty_history(self):
        result = estimate_likely_price([])
        self.assertIsNone(result["estimated"])
        self.assertEqual(result["confidence"], 0.0)


class TestPolicy(unittest.TestCase):
    def test_research_mode_blocks(self):
        settings = Settings(mode="research", allowed_venues={"a"})
        venue = type("V", (), {"id": "a", "permits_automation": True})()
        result = ExecutionPolicy(settings).evaluate(venue, Decimal("10"))
        self.assertFalse(result.allowed)

    def test_full_mode_requires_every_gate(self):
        venue = type("V", (), {"id": "a", "permits_automation": True})()
        settings = Settings(mode="full", kill_switch=False, allowed_venues={"a"}, tos_ack=True)
        self.assertTrue(ExecutionPolicy(settings).evaluate(venue, Decimal("10")).allowed)
        settings.tos_ack = False
        self.assertFalse(ExecutionPolicy(settings).evaluate(venue, Decimal("10")).allowed)


class TestPaperPipeline(unittest.TestCase):
    def test_paper_execution_is_simulated(self):
        adapter = PaperVenueAdapter({"id": "paper", "simulated": True})
        buy_ref = asyncio.run(adapter.execute_buy(None, None, None))
        sell_ref = asyncio.run(adapter.execute_sell(None, None, None))
        self.assertTrue(buy_ref.startswith("PAPER-BUY-"))
        self.assertTrue(sell_ref.startswith("PAPER-SELL-"))

    def test_end_to_end_scan_finds_paper_spread(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = os.path.join(tmp, "config")
            os.makedirs(config_dir)
            shutil.copy(root / "config" / "items.example.yaml", os.path.join(config_dir, "items.yaml"))
            shutil.copy(root / "config" / "venues.paper.example.yaml", os.path.join(config_dir, "venues.yaml"))

            settings = Settings(
                mode="research",
                db_path=os.path.join(tmp, "arbscout.db"),
                min_net_profit=Decimal("0"),
                min_roi_pct=Decimal("0"),
                min_confidence=0.0,
            )
            db.init_db(settings.db_path)
            venues = load_venues(config_dir)
            items = load_items(config_dir)
            summary = asyncio.run(scan_once(settings, venues, items, None, None))

            self.assertEqual(summary.quote_count, 4)
            self.assertGreaterEqual(summary.opportunity_count, 1)


if __name__ == "__main__":
    unittest.main()
