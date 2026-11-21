# ArbScout

A self-hosted research + arbitrage agent for **instant-quote game asset marketplaces** (sites that publish a price to buy coins/assets and an instant sell-back offer). It watches multiple venues, normalizes quotes, estimates fair value and likely sell-back prices, and surfaces "buy here → sell there" opportunities.

## What it does

- Collects quotes through **official APIs** and **public browser pages** (mixed per venue).
- Normalizes item identity, lot size, currency, and fees so quotes are comparable.
- Builds a per-item valuation model: median, robust spread, trend, and a "likely instant sell" estimate with a confidence score.
- Scores cross-venue arbitrage gaps after fees and payment spread.
- Offers three switchable operating modes: research, semi-automatic, and full-automatic.
- Keeps an append-only audit log of every scan, decision, approval, and execution attempt.

## Boundaries (important)

This project intentionally does **not** include:

- Stealth automation, anti-bot-detection evasion, fingerprint spoofing, CAPTCHA solving, or "make it look human" tooling.
- Unrestricted execution on venues that prohibit automation in their terms.
- Any mechanism to bypass logins, 2FA, account protections, or rate limits.

Browser access is scoped to an **allowlist of venues**, uses a transparent Playwright Chromium session, respects `robots.txt`, and applies conservative per-domain rate limits. Full-automatic execution is only possible for adapters that (a) you explicitly allow, (b) declare `permits_automation: true`, and (c) implement execution through an official API. The bundled example adapters are read-only placeholders.

Real-money trading of game assets commonly violates both marketplace terms and the game publisher's terms. Check the rules for every venue and game before using this tool. You are responsible for compliance and for any financial outcomes.

## Stack

- Python 3.12 + FastAPI + SQLite
- httpx for API adapters
- Playwright (Chromium) for read-only public-page adapters
- Dependency-free HTML/JS dashboard
- Docker Compose

## Quick start (simulated demo)

```sh
sh scripts/quickstart.sh
docker compose up --build
```

`quickstart.sh` creates `.env`, `config/items.yaml`, and `config/venues.yaml` from the paper-trading examples. Two simulated venues publish a persistent arbitrage spread and can execute fake orders, so you can run a scan, create a plan, approve it, and complete a full-automatic cycle with **no real money and no network calls**. Quotes and orders are tagged `simulated: true`.

- Dashboard: http://localhost:8000
- Health: http://localhost:8000/health
- API docs: http://localhost:8000/docs

To try full-auto: switch the mode to `Full` in the dashboard, then turn the kill switch off. The default is `research` with the kill switch **on**. To use real venues, replace `config/venues.yaml` with your own entries and set your own allowlist.

CI: `.github/workflows/test.yml` runs the static check and unit tests on every push. `.github/workflows/build-apk.yml` builds the APK on tags or manual dispatch.

## Web app and APK

Both targets use the **same** front end in `web/` — one design, one asset set, one 3D scene.

- **Web / PWA:** served by the FastAPI container at `http://localhost:8000`, installable via the browser's "Add to home screen".
- **APK:** a Capacitor Android shell that bundles `web/` verbatim. The Java/Kotlin layer contains no separate UI.

For a local APK build you need Node 20, JDK 17 and the Android SDK:

```sh
npm install
npx cap add android
npm run android:build     # output: android/app/build/outputs/apk/debug/app-debug.apk
```

**Without local tooling:** see `docs/GITHUB.md`. `scripts/setup-github.sh` creates and pushes the repo; `deploy-pages.yml` publishes the website; `release.yml` builds and attaches both the APK and a website zip to a GitHub Release on a `v*` tag. Netlify/Vercel configs and a standalone `docker-compose.web.yml` are also included. Point the app at your backend by opening `?api=https://your-backend:8000` once; the value is stored locally. Use HTTPS for the backend on Android (`allowMixedContent` is enabled for local testing).

## Design and assets

The front end is a scroll-driven 3D experience: a real glTF model with PBR textures, lit by a real HDRI environment map, rotating and drifting as the page scrolls, with glass panels and spring-like transitions. No design MCP server or design skill was available during the build, so assets were sourced and vendored from CC0/OFL libraries instead of being fabricated in code. See `ASSETS.md` for full credits and licences.

## Operating modes

| Mode | Behavior |
| --- | --- |
| `research` | Read-only collection and scoring. No login, no transactions. |
| `semi` | Builds an exact action plan and requires your approval before each step. |
| `full` | Executes end-to-end, but only through official-API adapters on your allowlist. Kill switch and spend caps still apply. |

Switch modes with `PUT /api/mode` or the dashboard. The kill switch is independent: `ARBSCOUT_KILL_SWITCH=true` blocks all execution regardless of mode.

## Configuration

`config/venues.yaml` defines adapters. Two kinds are supported:

- `api` — calls JSON endpoints and extracts fields with a small dot-path notation (`data.0.price`).
- `browser` — opens a public page, waits for a CSS selector, and reads visible text.

Each venue has a `permits_automation` flag. Read-only research works for any allowlisted venue; execution requires the flag plus an adapter that implements the execution methods.

`config/items.yaml` defines canonical items, lot sizes, and aliases. Aliases let different venues' names map to the same item key.

See `docs/ARCHITECTURE.md` for the data flow and extension points.

## API

Key endpoints:

- `GET /health`
- `GET /api/mode`, `PUT /api/mode`
- `GET /api/items`
- `POST /api/scan` (manual scan)
- `GET /api/opportunities`
- `POST /api/opportunities/{id}/plan`
- `POST /api/plans/{id}/approve`
- `POST /api/plans/{id}/execute`
- `GET /api/quotes?item_key=...`
- `GET /api/valuation/{item_key}`
- `GET /api/audit`
- `GET /api/settings`, `PATCH /api/settings`

## Limitations

- Venue layouts and APIs change; adapters need maintenance.
- Instant sell-back offers are usually **below** the buy price. Most pairs will not be profitable after fees — the tool tells you when they are, not the other way around.
- Confidence is statistical, not a guarantee. Thin or stale data produces low confidence and opportunities get filtered out.
- This is research software, not financial advice.

## License

Original code, MIT.
