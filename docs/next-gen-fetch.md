# Design: Next-Generation Price Fetching (fli migration)

**Status:** Accepted (pass 1 implemented 2026-11-05; live smoke pending — run one real HKG→NRT search + scheduler dry run before first production scheduler cycle)
**Date:** 2026-11-05
**Decision type:** Architectural

## 1. Problem

Both price-fetch paths are broken:

1. `src/services/scraper.py::scrape_prices` — plain `httpx` POST to
   `api.hkexpress.com/flt-booking-query/public/v1/availability/search` with a dummy
   `x-signature` header. The endpoint no longer accepts that (signature validation
   introduced upstream).
2. `src/services/scraper.py::scrape_prices_advanced` — patchright/Playwright
   fallback that boots a real Chrome profile, walks the caching site, and replays
   the same API with browser-forged headers. Equally broken and heavy (non-headless
   Chrome in a scheduled job).

Both target the HK Express booking API exclusively. There is no alternative
provider in the codebase; daily snapshots have been failing since breakage.

## 2. Decision

Replace the whole scraping layer with [`fli`](https://github.com/punitarani/fli)
(published on PyPI as **`flights`**): a maintained Python library that queries
**Google Flights** by serializing searches into the `tfs=` protobuf parameter and
reading results out of the public search page's inline JSON (`AF_initDataCallback`,
key `ds:1`). No browser, no HTML parsing.

Also in scope: making the fetch layer query-provider-neutral from the app's point
of view (adapter behind the existing `ScrapeResult` interface), and adding
per-itinerary search filters.

## 3. Why fli, and the accepted risk

- **Actively maintained** as of 2026-09 — the project tracks Google's protocol
  changes (the 2026-08 `x-goog-batchexecute-bgr` RPC gating forced the move to the
  page-transport approach; fli works with frequency of measured behavior).
- **Handles for us**: 10 req/s global token-bucket rate limiting, retry with
  exponential backoff, typed error hierarchy, currency/locale parameters.
- **It is still unofficial.** Google Flights can change or block at any time.
  This is accepted for a personal app; breakage risk moves from HK Express to
  Google, and the fetch surface is deliberately thin so a provider swap is a
  single module.

## 4. What fli gives and costs (facts)

- One-way, round-trip, and date-range searches; multi-city core is unsupported
  (client-side rendering behind the gated RPC) — irrelevant to this design.
- Filters: cabin class (4 values), max stops (4 values), include/exclude airline
  IATA lists, alliance include/exclude, layover bounds, departure window,
  passenger mix, currency/language/country. **No** "low-cost category" filter —
  express an LCC preference as an airline whitelist (e.g. `UO`,`GK`,`MM`,`7C`).
- Currency: native `curr=` param — we request the app's display currency directly.
  The FX layer stays as-is for conversion of historical snapshots and the
  configurable base-currency setting.
- Cost per page: **one-way = 1 fetch**; date range = 1 fetch per date (capped
  93); round trip = `1 + top_n` (default 5, max 10). fli self-limits to 10 req/s.
- Known limits: ~20-45 rows per response; children/infant parties can thin or
  empty the result set (Google prices those client-side); EU/EEA IPs need the
  SOCS consent cookie (fli sends a pre-accepted one by default,
  `FLI_SOCS_COOKIE` to override).
- Blockage detection: fli raises typed errors; a never-loadable sweep aborts.

## 5. Design

### 5.1 Fetch layer (replaces `scraper.py` internals)

New module `src/services/fli_search.py`:

- Public function keeps the scheduler's contract shape:
  `scrape_prices(queries, currency_code, filters=None) -> list[ScrapeResult]`,
  `ScrapeResult/Flight` dataclasses unchanged (fare, currency, flight_number,
  departure_at, arrival_at).
- Maps app models → fli models (`FlightSearchFilters` with `FlightSegment` per
  leg, `SeatType`, `MaxStops`, airline include/exclude lists). fli uses
  `Airport`/`Airline` **enums**, not IATA strings — the adapter does a
  string→enum lookup; an unknown code surfaces as a typed error row for that
  leg, never as a silently dropped filter.
- fli's `search()` may return `None` (empty) and `FlightResult.price` may be
  `None` (premium-cabin rows) — drop null-price rows **before** the top-N
  selection. Fresh `SearchFlights` instance per call (not thread-safe).
- Persists **top 3 cheapest rows** per leg per day into `FareSnapshot` —
  not all ~20-45 rows; history readable, DB small.
- One-way search **per leg**, priced independently. Rationale: 1 fetch per leg
  (day any round-trip `1+N`), and legs can be changed mid-trip without the
  coupling of paired searches. 37% rule math and existing schema untouched.
- Delete all HK Express code: both scrape paths, `_parse_hkexpress_response`,
  patchright profile handling, and the playwright/patchright/fake-useragent
  dependencies from `pyproject.toml`. Add `flights` via `uv`.

### 5.2 Filters & storage

- New optional columns on `Itinerary` (new Alembic revision, nullable =
  "global default applies"), stored as **`String` + app-level Python enum**
  (SQLite-safe; no native DB enum):
  - `cabin_class` — enum: ECONOMY / PREMIUM_ECONOMY / BUSINESS / FIRST
  - `max_stops` — enum: ANY / NON_STOP / ONE_STOP / TWO_PLUS_STOPS
  - `airlines` — JSON list of IATA codes (include-filter; empty = all)
- New setting-service defaults (global): same three concepts, so a user running
  only a single profile never touches per-itinerary fields.
- Per-itinerary value overrides the global default; `airlines` combines as
  include-list (empty = no restriction).

### 5.3 Scheduler & scrape wiring

- Currency: both call sites (`scheduler.scrape_fares`,
  `routes/api/itinerary.scrape_flight`) pass `get_configured_base_currency()`
  as the fetch currency so snapshots land in the user's base currency.
- The 37% rule input collapses snapshots per date — with multiple rows per day
  it must take **min fare per date** (regression guard; dict-comprehension
  "last-writing" collapse is now wrong). Fares are converted to the base
  currency before the r37 comparison, mirroring `_serialize_snapshot`.
- Failed leg = **one sentinel row** (`fare=None`, `scrape_status='error'`,
  message) per leg, in both write loops — otherwise a blocked day writes zero
  rows and is indistinguishable from "nothing to see".
- No new rate or concurrency logic — fli owns it.

### 5.5 Rate limiting — no disk cache

**Revised 2026-11 (final): there is no fare cache.** fli ships a global 10 req/s token bucket and the adapter issues one fetch per leg per invocation — repeat traffic is bounded by construction, so caching is redundant complexity for a dev-only benefit. Every call to `scrape_prices` fetches live data, production and dev alike. Rate-limit safety relies entirely on fli's built-in limiter.

### 5.6 Frontend (Vue / Inertia)

**API field contract (pinned):** reads return **camelCase**
(`cabinClass`, `maxStops`, `airlines` — CamelCaseJSONProvider); writes accept
**snake_case** body keys (`cabin_class`, `max_stops`, `airlines`), matching
existing route style; settings form reads `props.settings.*` camelCase, writes
snake_case.

**Submission surface (revised 2026-11):** rides the existing endpoints —
`Create.vue` → `POST /api/itineraries`, `Detail.vue` inline filter editor →
`PATCH /api/itineraries/<id>` (backend must accept the three filter keys
there), settings → existing settings patch path. Form-CRUD-over-API is
grandfathered per the STYLE.md Inertia-first rule; migrating it is a separate
future pass.

- Itinerary create/edit: cabin dropdown, stops dropdown, airlines — multiselect
  of common carriers (UO, GK, MM, 7C, CX, JL, TR, …) **plus** free-text input
  for any other IATA code. `Create.vue` carries the fields from creation; the
  edit surface is a compact inline filter editor on `Detail.vue` using the
  existing PATCH endpoint (no redesign of the page).
- Settings page: the same three controls acting as global defaults.
- All controls optional; empty = default.
- Option lists (cabin, stops, common carriers) defined once in a shared exported
  const module and reused by both surfaces — no drift between form and settings.

## 6. Implementation scope & verification

Backend lane owns: `src/services/fli_search.py`, deletion of
`src/services/scraper.py`, `pyproject.toml`/`uv.lock`, the Alembic revision,
`src/extensions/database.py`, `src/services/setting.py`,
`src/routes/api/settings.py` (per-namespace allowlists) ,
`src/routes/pages/settings.py` + `src/routes/pages/itinerary.py` (Inertia
props), `scheduler.py`, `routes/api/itinerary.py` incl. on-demand endpoint,
`Dockerfile` (remove the patchright install line), README/STYLE/AGENTS doc
updates for the removed module, tests/backend.
Frontend lane owns: `src/frontend/**` and `tests/frontend/**` only.

Verification:
1. `uv run pytest` (backend), `npm run lint`, `npm run type-check`, `npm run test`.
2. Fresh SQLite: `flask db upgrade` applies the new revision cleanly.
3. Live smoke: one real search (e.g. HKG→NRT via adapter) to confirm legal
   `tfs` encoding, followed by one scheduler run confirming snapshot rows,
   including one airline-filtered search.
4. Property tests for the filter-merge helper (per-itinerary vs global default)
   using hypothesis.

## 7. Explicitly out of scope

- Round-trip / itinerary coupling (per-leg pricing only).
- Alerting/retry dashboards for blockage days (log + error rows suffice).
- Migrating FX or the 37% rule.
- Any UI redesign beyond adding the three filter controls.
