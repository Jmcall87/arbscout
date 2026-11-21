from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import Any, Iterator, Sequence

from .models import AuditEntry, Opportunity, Plan, PlanStep, Quote

SCHEMA = """
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue TEXT NOT NULL,
    item_key TEXT NOT NULL,
    side TEXT NOT NULL,
    price TEXT NOT NULL,
    currency TEXT NOT NULL,
    units_per_lot TEXT NOT NULL,
    fee_pct TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence REAL NOT NULL,
    raw TEXT
);
CREATE INDEX IF NOT EXISTS idx_quotes_item_time ON quotes(item_key, captured_at);

CREATE TABLE IF NOT EXISTS opportunities (
    id TEXT PRIMARY KEY,
    item_key TEXT NOT NULL,
    buy_venue TEXT NOT NULL,
    buy_price TEXT NOT NULL,
    sell_venue TEXT NOT NULL,
    sell_price TEXT NOT NULL,
    gross_spread TEXT NOT NULL,
    buy_fee TEXT NOT NULL,
    sell_fee TEXT NOT NULL,
    payment_spread TEXT NOT NULL,
    net_profit TEXT NOT NULL,
    roi_pct TEXT NOT NULL,
    confidence REAL NOT NULL,
    risk_flags TEXT NOT NULL,
    captured_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_opportunities_time ON opportunities(captured_at);

CREATE TABLE IF NOT EXISTS plans (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    steps TEXT NOT NULL,
    approval_required INTEGER NOT NULL,
    approved INTEGER NOT NULL,
    executed INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    reason TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event TEXT NOT NULL,
    detail TEXT NOT NULL,
    mode TEXT NOT NULL,
    allowed INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@contextmanager
def connect(path: str) -> Iterator[sqlite3.Connection]:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(path: str) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA)


def _dump(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, default=str)


def _load(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def quote_from_row(row: sqlite3.Row) -> Quote:
    return Quote(
        venue=row["venue"],
        item_key=row["item_key"],
        side=row["side"],
        price=Decimal(row["price"]),
        currency=row["currency"],
        units_per_lot=Decimal(row["units_per_lot"]),
        fee_pct=Decimal(row["fee_pct"]),
        captured_at=datetime.fromisoformat(row["captured_at"]),
        source=row["source"],
        confidence=float(row["confidence"]),
        raw=_load(row["raw"], {}),
    )


def opportunity_from_row(row: sqlite3.Row) -> Opportunity:
    return Opportunity(
        id=row["id"],
        item_key=row["item_key"],
        buy_venue=row["buy_venue"],
        buy_price=Decimal(row["buy_price"]),
        sell_venue=row["sell_venue"],
        sell_price=Decimal(row["sell_price"]),
        gross_spread=Decimal(row["gross_spread"]),
        buy_fee=Decimal(row["buy_fee"]),
        sell_fee=Decimal(row["sell_fee"]),
        payment_spread=Decimal(row["payment_spread"]),
        net_profit=Decimal(row["net_profit"]),
        roi_pct=Decimal(row["roi_pct"]),
        confidence=float(row["confidence"]),
        risk_flags=_load(row["risk_flags"], []),
        captured_at=datetime.fromisoformat(row["captured_at"]),
    )


def plan_from_row(row: sqlite3.Row) -> Plan:
    steps = [PlanStep(**step) for step in _load(row["steps"], [])]
    return Plan(
        id=row["id"],
        opportunity_id=row["opportunity_id"],
        mode=row["mode"],
        steps=steps,
        approval_required=bool(row["approval_required"]),
        approved=bool(row["approved"]),
        executed=bool(row["executed"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        reason=row["reason"],
    )


def insert_quotes(path: str, quotes: Sequence[Quote]) -> None:
    if not quotes:
        return
    rows = [
        (
            quote.venue,
            quote.item_key,
            quote.side,
            str(quote.price),
            quote.currency,
            str(quote.units_per_lot),
            str(quote.fee_pct),
            quote.captured_at.isoformat(),
            quote.source,
            quote.confidence,
            _dump(quote.raw),
        )
        for quote in quotes
    ]
    with connect(path) as conn:
        conn.executemany(
            """INSERT INTO quotes
               (venue, item_key, side, price, currency, units_per_lot, fee_pct,
                captured_at, source, confidence, raw)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )


def get_quotes(path: str, item_key: str | None = None, limit: int = 200) -> list[Quote]:
    with connect(path) as conn:
        rows = conn.execute(
            """SELECT * FROM quotes
               WHERE (? IS NULL OR item_key = ?)
               ORDER BY captured_at DESC, id DESC
               LIMIT ?""",
            (item_key, item_key, max(1, limit)),
        ).fetchall()
    return [quote_from_row(row) for row in reversed(rows)]


def save_opportunities(path: str, opportunities: Sequence[Opportunity]) -> None:
    if not opportunities:
        return
    rows = [
        (
            opp.id,
            opp.item_key,
            opp.buy_venue,
            str(opp.buy_price),
            opp.sell_venue,
            str(opp.sell_price),
            str(opp.gross_spread),
            str(opp.buy_fee),
            str(opp.sell_fee),
            str(opp.payment_spread),
            str(opp.net_profit),
            str(opp.roi_pct),
            opp.confidence,
            _dump(opp.risk_flags),
            opp.captured_at.isoformat(),
        )
        for opp in opportunities
    ]
    with connect(path) as conn:
        conn.executemany(
            """INSERT OR REPLACE INTO opportunities
               (id, item_key, buy_venue, buy_price, sell_venue, sell_price,
                gross_spread, buy_fee, sell_fee, payment_spread, net_profit,
                roi_pct, confidence, risk_flags, captured_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )


def list_opportunities(path: str, limit: int = 100, profitable_only: bool = True) -> list[Opportunity]:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT * FROM opportunities ORDER BY captured_at DESC, id DESC LIMIT ?",
            (max(1, limit) * 4),
        ).fetchall()
    result = [opportunity_from_row(row) for row in rows]
    if profitable_only:
        result = [opp for opp in result if opp.net_profit > 0]
    return result[:limit]


def get_opportunity(path: str, opportunity_id: str) -> Opportunity | None:
    with connect(path) as conn:
        row = conn.execute(
            "SELECT * FROM opportunities WHERE id = ?", (opportunity_id,)
        ).fetchone()
    return opportunity_from_row(row) if row else None


def save_plan(path: str, plan: Plan) -> None:
    with connect(path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO plans
               (id, opportunity_id, mode, steps, approval_required, approved,
                executed, created_at, reason)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                plan.id,
                plan.opportunity_id,
                plan.mode,
                _dump([step.model_dump(mode="json") for step in plan.steps]),
                int(plan.approval_required),
                int(plan.approved),
                int(plan.executed),
                plan.created_at.isoformat(),
                plan.reason,
            ),
        )


def get_plan(path: str, plan_id: str) -> Plan | None:
    with connect(path) as conn:
        row = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    return plan_from_row(row) if row else None


def list_plans(path: str, limit: int = 100) -> list[Plan]:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT * FROM plans ORDER BY created_at DESC LIMIT ?", (max(1, limit),)
        ).fetchall()
    return [plan_from_row(row) for row in rows]


def append_audit(path: str, entry: AuditEntry) -> None:
    with connect(path) as conn:
        conn.execute(
            """INSERT INTO audit (timestamp, event, detail, mode, allowed)
               VALUES (?, ?, ?, ?, ?)""",
            (
                entry.timestamp.isoformat(),
                entry.event,
                entry.detail,
                entry.mode,
                int(entry.allowed),
            ),
        )


def list_audit(path: str, limit: int = 100) -> list[AuditEntry]:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT * FROM audit ORDER BY id DESC LIMIT ?", (max(1, limit),)
        ).fetchall()
    return [
        AuditEntry(
            id=row["id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            event=row["event"],
            detail=row["detail"],
            mode=row["mode"],
            allowed=bool(row["allowed"]),
        )
        for row in rows
    ]


def get_settings(path: str) -> dict[str, str]:
    with connect(path) as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: row["value"] for row in rows}


def set_setting(path: str, key: str, value: str) -> None:
    with connect(path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
