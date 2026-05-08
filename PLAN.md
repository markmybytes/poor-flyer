# Airline Price Scraper — Implementation Plan

## Tech Stack

- **Backend**: Python 3.12 + Flask + Jinja2 (server-rendered, no React)
- **Database**: SQLite via SQLAlchemy (sync)
- **Scheduler**: APScheduler — daily scrape job at 09:00 UTC
- **HTTP client**: `httpx` (sync; swap to Selenium later by replacing `scraper.py` only)
- **Charts**: Chart.js via CDN (no build step)
- **CSS**: Tailwind CSS via CDN (no build step)
- **Container**: Single Docker service + `docker-compose.yml`

> **Round-trip tracking**: Each tracking entry is always one-way. To track a round trip, create two entries (e.g. HKG→NRT and NRT→HKG).

---

## Database Schema

### `tracking_entries`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT | PK (UUID) |
| `name` | TEXT | User label, optional |
| `origin` | TEXT | e.g. `HKG` |
| `destination` | TEXT | e.g. `NRT` |
| `flight_date` | DATE | The specific flight date to track |
| `adult_count` | INT | default 1 |
| `child_count` | INT | default 0 |
| `infant_count` | INT | default 0 |
| `deadline` | DATE | optional buy deadline; enables Deadline 37% rule |
| `is_active` | BOOL | controls scraping |
| `created_at` | DATETIME | |

### `price_snapshots`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT | PK (UUID) |
| `entry_id` | TEXT | FK → tracking_entries (CASCADE DELETE) |
| `scraped_at` | DATETIME | |
| `fare` | DECIMAL | Lowest `display_item_amount` (U_LITE base fare, no taxes) |
| `flight_number` | TEXT | Flight with cheapest fare |
| `departure_time` | TEXT | e.g. `01:15` |
| `arrival_time` | TEXT | |
| `scrape_status` | TEXT | `success` or `error` |
| `error_message` | TEXT | null on success |

---

## HKExpress API

**Endpoint:** `POST https://api.hkexpress.com/flt-booking-query/public/v1/availability/search`

**Headers:**
```
content-type: application/json
x-signature: dummy
origin: https://mybooking.hkexpress.com
referer: https://mybooking.hkexpress.com/
user-agent: Mozilla/5.0 ...
```

No cookies sent. If the API rejects the request, the error is stored in the snapshot.

**Body:**
```json
{
  "application_code": "IBE",
  "flights": [{"origin": "HKG", "destination": "NRT", "begin_date": "2026-06-01"}],
  "currency_code": "HKD",
  "promotion_code": "",
  "passengers": {"adult_count": 1, "infant_count": 0, "children_count": 0}
}
```

**Parsing logic:**
1. `trip[0].journey` → pick the journey with the lowest `display_item_amount` → `fare`
2. Record `flight_number`, `departure_time`, `arrival_time` from that journey's first segment
3. If response is non-200, no `trip`, or no valid journeys → snapshot with `scrape_status = 'error'`

---

## 37% Rule Logic (`src/rule37.py`)

Computed on-the-fly from snapshots (never stored). Two rule types **always co-exist** on every entry.

### Deadline Rule 37 (`DeadlineRule37`)

Only active when `deadline` is set. Key date = `created_at + (deadline − created_at) × 0.37`.

```
key_date = created_at + (deadline - created_at) * 0.37

if today < key_date:
    phase = OBSERVING

else:
    min_observed = min(fare of snapshots scraped before key_date)
    if latest_fare < min_observed:
        phase = BUY_SIGNAL
    else:
        phase = WAITING
```

### Dynamic Rule 37 (`DynamicRule37`)

Always computed. Observation window = first 37% of all successful snapshots collected so far.

```
obs_count = floor(total_successful_snapshots * 0.37)

if obs_count == 0:          # < 3 snapshots → not enough data
    phase = OBSERVING
else:
    min_observed = min(fare of first obs_count snapshots)
    if latest_fare < min_observed:
        phase = BUY_SIGNAL
    else:
        phase = WAITING
```

The dynamic cutoff shifts outward as more data is collected. Both types are shown simultaneously on the detail page.

---

## Stop Fetching Rules

Scraping is skipped (scheduler and Scrape Now button) when:
- `is_active = False`, OR
- `flight_date < today` (departure has passed)

---

## Web UI Pages

### Create Page — `GET /create`

Form fields:
- **Label** (text, optional)
- **From** (text, e.g. `HKG`)
- **To** (text, e.g. `NRT`)
- **Flight Date** (date picker)
- **Buy Deadline** (date picker, optional) — enables Deadline 37% rule; key date auto-calculated
- **Passengers**: Adults (default 1), Children (default 0), Infants (default 0)
- **Submit** → `POST /entries` → redirect to `/`

### List / Index Page — `GET /`

Two sections:

**Summary section** — stat cards per entry (low / current / high fare + signal badges):

| HKG→NRT Jun 1 | | HKG→TYO Jul 30 |
|---|---|---|
| Low 680 · Now 770 · High 950 | | Low 1100 · Now 1300 · High 1500 |
| 🟡 Deadline: Watching · 🟢 Dynamic Buy | | 🟢 Deadline Buy · ⚪ Dynamic: Wait |

**Entry list section** — one card per entry with action buttons:

```
HKG → NRT  Active  Flight Jun 01 2026  Deadline May 31  1 adult  Scraped May 07 09:00
[View]  [Disable]  [Delete]
```

### Detail Page — `GET /detail/{id}`

**Header section:**
- Route: `HKG → NRT | Jun 01 2026`
- Passengers: `1 adult`
- Buy deadline (if set): `May 31 2026`
- Buttons: [Enable/Disable] [Scrape Now] (hidden if past departure) [← Back to list]

**37% Analysis — two side-by-side panels:**

*Dynamic 37% Rule* (always shown):
- Status badge: `🟡 OBSERVING — 2 snapshots collected` or `🟢 BUY SIGNAL — Current HKD 770 vs best HKD 820`
- Footer: `Observation window: 7 of 19 snapshots`

*Deadline 37% Rule* (shown only when deadline is set):
- Key date: `May 12, 2026` (5 days away)
- Status badge: `🟡 OBSERVING` / `🟢 BUY SIGNAL` / `⚪ WAITING`
- Card has a green ring when BUY SIGNAL

**Two tabs: Table | Graph** (JS tab-switch, no page reload)

**Table tab:**

- Rows newest-first
- Separator `↑ After observation · ↓ Dynamic 37% observation (N of M)` between action and observation windows
- Separator `↑ After key date · ↓ Deadline 37% observation (key date: ...)` when crossing deadline key date
- Observation rows: amber background; best-price row: green; error rows: red
- Legend at bottom

**Graph tab:**

- X axis: Date Scraped
- Y axis: Fare (HKD)
- Blue line + dots; amber dots for observation-window points

---

## Scheduler (`src/scheduler.py`)

- `APScheduler BackgroundScheduler` started when Flask app starts
- Daily job at **09:00 UTC**: iterates entries where `is_active = True` **and** `flight_date >= today`, calls `scraper.scrape()`, writes a `PriceSnapshot`
- No retry — next attempt is the following day
- "Scrape Now" on the detail page triggers the same logic via `POST /entries/{id}/scrape` (returns 400 if flight date has passed)

---

## Project Structure

```
airline-price-scraper/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .gitignore                  # ignores /data, .venv, __pycache__
├── PLAN.md
├── data/                       # gitignored; Docker volume mount for SQLite
└── src/
    ├── __init__.py             # create_app() factory
    ├── database.py             # SQLAlchemy models + db session setup
    ├── scraper.py              # sync httpx HKExpress client + parser
    ├── rule37.py               # Rule37Status computation (pure functions)
    ├── scheduler.py            # APScheduler setup + daily scrape job
    ├── routes/
    │   ├── __init__.py
    │   ├── pages.py            # Blueprint: GET /  /list  /detail/<id>
    │   └── api.py              # Blueprint: POST /entries, toggle, delete, scrape
    ├── templates/
    │   ├── base.html           # nav, Tailwind CDN, Chart.js CDN
    │   ├── create.html         # create form
    │   ├── list.html           # tracking entries table
    │   └── detail.html         # detail view with table + graph tabs
    └── static/
        └── app.js              # Chart.js init, tab switching, form mode toggle
```

---

## Docker

**`Dockerfile`:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
CMD ["gunicorn", "src:create_app()", "--bind", "0.0.0.0:8000", "--workers", "1"]
```

**`docker-compose.yml`:**
```yaml
services:
  web:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - DATABASE_URL=sqlite:////app/data/db.sqlite
    restart: unless-stopped
```

---

## Key Dependencies (`requirements.txt`)

```
flask
sqlalchemy
httpx
apscheduler
gunicorn
```

---

## Implementation Order

1. `src/database.py` — SQLAlchemy models + session helpers
2. `src/scraper.py` — sync HKExpress client + parser
3. `src/rule37.py` — pure 37% computation
4. `src/routes/api.py` — form POST endpoints (create, toggle, delete, scrape)
5. `src/routes/pages.py` — HTML page routes
6. `src/scheduler.py` — APScheduler daily job
7. `src/__init__.py` — `create_app()` factory wiring it all together
8. `templates/` — all 4 templates + `static/app.js`
9. `Dockerfile` + `docker-compose.yml` + `requirements.txt` + `.gitignore`
