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

Computed on-the-fly from snapshots (never stored). Only **Deadline Rule 37** is used.

### Deadline Rule 37 (`DeadlineRule37`)

Only computed when `deadline` is set. Key date = `created_at + (deadline − created_at) × 0.37`.

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

If no deadline is set, returns `None` and no 37% rule is applied.

---

## Stop Fetching Rules

Scraping is skipped (scheduler and Scrape Now button) when:
- `is_active = False`, OR
- `flight_date < today` (departure has passed)

---

## Web UI Pages

### List / Index Page — `GET /`

One integrated card per entry with all info:

```
┌──────────────────────────────────────────────────────────────┐
│ HKG → NRT  Tokyo Summer        Active                        │
│ Jun 07, 2026 · 1A, 1I                                        │
├──────────────────────────────────────────────────────────────┤
│ Low 671 · Now 727 · High 765 · Key Date 06/02               │
├──────────────────────────────────────────────────────────────┤
│ 🟡 OBSERVING    [View] [Disable] [Delete]                   │
└──────────────────────────────────────────────────────────────┘
```

- Route, date, label, passenger count
- Price stats (Low / Current / High) + deadline key date
- 37% status badge (BUY SIGNAL / OBSERVING / WAITING) or "No deadline"
- Action buttons

### Detail Page — `GET /detail/{id}`

**Header section:**
- Route: `HKG → NRT | Jun 07 2026`
- Label, passengers, deadline (if set)
- Buttons: [Enable/Disable] [Scrape Now] (hidden if past departure) [← Back to list]

**37% Rule status** (if deadline set):
- Key date display
- Phase badge: `🟢 BUY SIGNAL` / `🟡 OBSERVING` / `⚪ WAITING`
- Current fare vs. best observed

**Daily collapsible groups:**
- Each day appears as a collapsible section, grouped newest-first
- Header shows: date + lowest price that day + flight count
- Click to expand → shows all flights for that day in table format

**Color coding:**
- 🔵 **BLUE**: All-time low price (lowest in entire dataset)
- 🟢 **GREEN**: 37% observation best (min_observed)
- 🔴 **RED**: Missing price (scrape error)
- ⚪ **NO COLOR**: Regular snapshots

**Key date bar:**
- Blue separator bar showing the 37% key date (if deadline set)

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
