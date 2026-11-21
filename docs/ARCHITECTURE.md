# Architecture

## Data flow

```
venues.yaml / items.yaml
        |
        v
VenueRegistry -> VenueAdapter.fetch_quotes()  (httpx API or Playwright browser)
        |
        v
normalization.normalize_quote()   -> comparable Quote objects
        |
        +--> SQLite `quotes` table (history)
        |
        v
valuation.build_valuation()       -> fair value, likely sell price, confidence
        |
        v
scanner.compute_opportunities()   -> buy venue / sell venue pairs
        |
        +--> SQLite `opportunities`
        |
        v
execution.plan() -> approval? -> execute() -> audit log
```

## Key modules

- `app/config.py` — environment settings and mode parsing.
- `app/models.py` — Pydantic schemas shared by API and storage.
- `app/db.py` — small sqlite3 wrapper; one connection per operation.
- `app/normalization.py` — item keys, money parsing, fee math.
- `app/research/market.py` — robust statistics and trend estimation.
- `app/valuation.py` — per-item valuation from quote history.
- `app/venues/` — adapter interface, API adapter, browser adapter, YAML registry.
- `app/browser/session.py` — shared Playwright session with robots.txt check and per-domain rate limiting.
- `app/execution/` — policy gate, action plans, approvals, executor.
- `app/scanner.py` — scheduled and manual scan orchestration.
- `app/router.py` — HTTP API.

## Extension points

To add a venue, add an entry to `config/venues.yaml`. For more complex sites, subclass `VenueAdapter` in `app/venues/` and register it in `registry.py`. The bundled `paper` adapter is a deterministic simulator used by `scripts/quickstart.sh`; it implements execution with fake order references and tags all output `simulated: true`.

Execution is opt-in per adapter. The base class raises `NotImplementedError` for `execute_buy`/`execute_sell`; only adapters that use a documented official API should override them.

## Safety model

1. `mode` must be `full`.
2. `kill_switch` must be false.
3. Venue must be in `allowed_venues`.
4. Venue must declare `permits_automation: true`.
5. Adapter must implement execution.
6. `tos_ack` must be true.
7. Per-trade and per-day spend caps apply.

All seven checks are logged to the audit table on success and failure.
