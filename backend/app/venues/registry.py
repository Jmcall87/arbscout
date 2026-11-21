from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import yaml

from ..models import Item
from ..normalization import parse_money
from .api_adapter import ApiVenueAdapter
from .base import VenueAdapter
from .browser_adapter import BrowserVenueAdapter
from .paper_adapter import PaperVenueAdapter


def _read_yaml(folder: str, filename: str) -> dict[str, Any]:
    primary = os.path.join(folder, filename)
    example = os.path.join(folder, filename.replace(".yaml", ".example.yaml"))
    path = primary if os.path.exists(primary) else example
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_items(config_dir: str = "/app/config") -> list[Item]:
    data = _read_yaml(config_dir, "items.yaml")
    items: list[Item] = []
    for raw in data.get("items", []):
        if "key" not in raw:
            continue
        lot = parse_money(raw.get("lot_size", 1), Decimal("1")) or Decimal("1")
        items.append(
            Item(
                key=str(raw["key"]),
                game=str(raw.get("game", "")),
                name=str(raw.get("name", "")),
                unit=str(raw.get("unit", "")),
                lot_size=lot,
                currency=str(raw.get("currency", "USD")),
                aliases=[str(alias) for alias in raw.get("aliases", [])],
            )
        )
    return items


def load_venues(config_dir: str = "/app/config") -> list[VenueAdapter]:
    data = _read_yaml(config_dir, "venues.yaml")
    adapters: list[VenueAdapter] = []
    for config in data.get("venues", []):
        if not isinstance(config, dict):
            continue
        kind = str(config.get("kind", "api")).lower()
        if kind == "api":
            adapters.append(ApiVenueAdapter(config))
        elif kind == "browser":
            adapters.append(BrowserVenueAdapter(config))
        elif kind == "paper":
            adapters.append(PaperVenueAdapter(config))
    return adapters
