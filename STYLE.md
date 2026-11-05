# STYLE.md — Coding Style Guide

Canonical coding conventions for both humans and AI agents in the poor-flyer project.

## How To Use This Guide

- Treat this document as team guidance for consistency.
- Apply recommendations with judgment based on context.
- If two rules conflict, apply the priority order below.

## Rule Priority Order

1. Security and access control
2. Correctness and data integrity
3. Existing architecture and file placement
4. Simplicity and readability
5. Local consistency with nearby code

## Core Principles

- Prefer simple, direct solutions over premature abstraction.
- **Global YAGNI Threshold**: Keep execution logic straightforward, procedural, and inline (e.g., inside a blueprint view function or scheduler job) until triggered by:
  1. **Code Reuse**: The exact logic is explicitly required by another system entry point (e.g., a `flask` CLI command or a second scheduler job).
  2. **Feature Creep**: The single block grows beyond a readable screen (> 100 lines) or accumulates unrelated side-effects (e.g., sending notifications, audit logging loops, or cache clearing steps).
- Keep logic concise and avoid single-use helpers unless reuse is clear.
- Avoid intermediate variables when direct expressions remain readable.
- Ask for clarification when requirements are ambiguous.

## Naming Conventions

- Database tables: plural `snake_case` (e.g. `fare_snapshots`).
- URL routes: `kebab-case` segments.
- Database columns: `snake_case` — they are exposed to the frontend in `camelCase` by `CamelCaseJSONProvider` (`src/utils/transform.py`); do not rename columns to satisfy frontend spelling.
- Python modules, functions, variables: `snake_case`.
- Python classes: `PascalCase`; Pydantic models and dataclasses: `PascalCase`; type aliases: `PascalCase`.
- Python constants: `UPPER_SNAKE_CASE`.
- JavaScript / TypeScript functions, methods, variables: `camelCase`; types/interfaces: `PascalCase`; component file names: `PascalCase.vue`.

## Architecture And Placement

- Build routes through Flask blueprints; do not register views directly on `app`.
- Keep concerns in established locations:
  - Web (Inertia) views: `src/routes/pages/`
  - API (JSON) views: `src/routes/api/`
  - Services / domain logic: `src/services/`
  - Pure helpers (no Flask globals, no I/O): `src/utils/`
  - Flask extension singletons + `init_extensions(app)`: `src/extensions/`
  - SQLAlchemy models: `src/extensions/database.py` (shared `Base` / `db`)
  - Pages: `src/frontend/Pages/`
  - Shared components: `src/frontend/Components/`
  - Layouts: `src/frontend/Layouts/`
- Keep blueprint views thin; move non-trivial business logic to services or scheduler jobs.
- Scheduled job code lives in `src/services/scheduler.py`; reusable workhorse functions (e.g. `scrape_prices`, `convert_amount`) live in their owning service module.

## Backend Rules (Python / Flask)

- Use type hints on every public function signature, including return types. SQLAlchemy 2 `Mapped[T]` / `Mapped[T | None]` style is required for model attributes.
- Use `from __future__ import annotations` in modules that benefit (migrations, anything with forward references or many string literals).
- Prefer `collections.abc` types (`Mapping`, `Sequence`, `Iterable`) for **parameters**; prefer concrete builtins (`list`, `dict`) for **return types** — this matches how the rest of the standard library is annotated.
- Reach for `pathlib.Path` everywhere; never `os.path.join` for new code.
- Return Inertia pages from web (page) views via `flask_inertia.render_inertia`.
- Return structured JSON from API views following the API response contract below.
- Use `flask.g.tz` for the per-request timezone; never read `os.environ['TZ']` from inside a view.
- Use `current_app.config[...]` for runtime config; reach for `os.getenv` only in `create_app()`.

### Logging

- One module-level logger per file: `logger = logging.getLogger(__name__)`.
- Use `%`-format placeholders with the data as a second argument: `logger.info('x=%s', x)`. Never f-string into log calls — the format string is what lazy formatters and aggregators key off.
- Use `logger.exception(...)` only inside an `except` block. Use `logger.warning(..., exc_info=False)` when you mention an exception outside its handler.

### Exception Handling

- Catch the narrowest exception class that expresses the failure (`FXRatesError`, `KeyError`, `ValueError`, ...). Never `except Exception:` at module top level unless you immediately re-raise, convert to a 5xx envelope, or rollback the session.
- In scheduler jobs, wrap the body in `try/except/finally` and `db.session.rollback()` on error, `db.session.remove()` in `finally` — long-lived sessions leak identity-map state across iterations.
- Prefer `contextlib.suppress(SpecificError)` for "tried and tolerated" paths over `try: ... except: pass`.

### Enums For Finite Status Fields

- Use `enum.StrEnum` (Python 3.11+) for finite status fields stored as `String` columns. The repo currently keeps `scrape_status`, `trip_type`, and `Phase` as plain strings/enum — promote new finite fields to `StrEnum` so the column type, the Python value, and the JSON output are the same string and typos fail at import time.

```python
class ScrapeStatus(StrEnum):
    SUCCESS = 'success'
    ERROR = 'error'

# Model
scrape_status: Mapped[ScrapeStatus] = mapped_column(String, default=ScrapeStatus.SUCCESS)
```

### Concurrency For I/O Fan-Out

- For bounded I/O fan-out (e.g. sending N emails in parallel from a scheduler job) prefer `concurrent.futures.ThreadPoolExecutor` with a small `max_workers` over hand-rolled `threading.Thread(daemon=True).start()` — the executor gives you a context manager, deterministic shutdown, and `.result()` access.
- Background threads are fine for fire-and-forget notifications. Never share SQLAlchemy sessions across threads.

### Eager Loading

- SQLAlchemy collections must not lazy-load inside a JSON-serialising view. Always start from an explicit `select(...)` with the right `options(...)`:

```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

stmt = (
    select(Itinerary)
    .options(selectinload(Itinerary.flights).selectinload(Flight.fare_snapshots))
    .order_by(Itinerary.created_at)
)
```

- `selectinload` for collections (`list[...]`).
- `joinedload` for single-row relationships (`ManyToOne` / `OneToOne`).
- Always finish chains that join a collection with `.unique()` on the parent to avoid duplicate rows.
- Never depend on `lazy='select'` behaviour implicitly — if a relationship will be serialised, declare it in the same `options(...)` as the parent.

### Application-Owned Cache Keys

- Application-owned cache keys use lowercase colon-separated segments in stable order, with schema version last: `<domain>:<purpose>[:<scope-or-variant>...]:v<schema>`. Hash long or sensitive identifiers; use `v1` unless the cached payload shape changes. Package/vendor-managed keys retain their package-defined names.

### Migrations

- Make every Alembic revision reversible with a working `downgrade()`. Mirror every schema change in both directions.
- Additive columns: declare `nullable=True` and supply a `server_default` so the upgrade is non-blocking on populated tables.
- SQLite is in batch mode (`render_as_batch=True`), but type changes that are not portable to SQLite still need to be split into two revisions — check before relying on the batch behaviour.
- Do not edit a revision file after it has been merged — write a new revision.
- After model edits, run `uv run flask db migrate`, **review the autogenerated diff**, rename the revision sensibly, then `uv run flask db upgrade` to apply it locally.

### Blueprint & Route Architecture

Blueprint views should focus on request handling, validation, delegating to services, and returning the correct response shape. Inline processing or formatting is fine under the global YAGNI threshold.

#### 1. The Blueprint View as an Orchestrator

A view function is best when it limits itself to: parsing the request, performing authorisation/validation, delegating to a service, and returning a response.

- Inline processing, data formatting, or short loops are fine inside a view under the YAGNI threshold.
- Move processing into `src/services/*.py` only when the logic needs to be reused (e.g. by a CLI command or a scheduler job) or exceeds a single readable screen of over 100 lines.

#### 2. File Separation Boundaries (When to Split)

Create a new blueprint or module when:

- **Context Isolation**: Separating public-facing flows from internal admin flows prevents role-checking logic from polluting queries and view rendering.
- **Pivot Attributes**: A child relationship has unique, highly mutable parameters that would clutter a parent resource file.
- **Resource Cohesion**: Avoid grouping entirely distinct underlying models or unrelated view modules into a single file.

#### 3. Inertia First; JSON API by Exception

Inertia routes are the default for page reads, forms, CRUD, redirects, and mutations. Reserve API routes for independent JSON interactions that must avoid an Inertia visit: polling, job-status queries, data queries, or isolated state updates (e.g., status toggles, inline sort). API is not for ordinary form submission or general SPA replacement.

- Use native `fetch`. Check `response.ok` explicitly — `fetch` does not reject on HTTP 4xx/5xx.
- Manually sync returned state: apply the response in the success path to keep the UI accurate with the database (Frontend Sync Tax).
- Triggered background actions (e.g. on-demand fare scrape) stay in an API endpoint under `src/routes/api/`. Mount it under `api_bp` with the standard envelope; the Vue component applies the response inside the successful `.then` block.
- **Safeguard Against File Explosion**: Do not create a standalone blueprint file for every single endpoint. Group related actions for the same model inside a single, cohesive API blueprint using semantic endpoint naming:

```python
# src/routes/api/itinerary.py — Cohesive grouping within a single blueprint
itineraries_bp = Blueprint("itineraries", __name__, url_prefix="/itineraries")

@itineraries_bp.patch("/<itinerary_id>/status")
def update_status(itinerary_id: str):
    ...

@itineraries_bp.patch("/<itinerary_id>/ordering")
def update_sort_order(itinerary_id: str):
    ...
```

- Legacy note: form-CRUD over `/api/*` (e.g. `Create.vue` POST `/api/itineraries`) predates this rule and is grandfathered — do not carry the pattern into new surfaces; migrating it is a dedicated pass, not incidental work.

#### 4. Nested Route Ownership

Express ownership at the route layer, business rules in the view:

```python
# Good: parent-child ownership via URL prefix + scoped view
@itineraries_bp.route("/<itinerary_id>/packages", ...)
def packages_index(itinerary_id: str): ...


# Good: domain invariant inside the view (using a guarded query)
package = (
    db.session.execute(
        select(Package).where(Package.id == pkg_id, Package.itinerary_id == itinerary_id)
    ).scalar_one_or_none()
)


# Avoid: ownership concern leaked into the view body
if package.itinerary_id != itinerary_id:
    abort(404)
```

When the parent ownership check is heavy or cross-resource, register a `before_request` on the nested blueprint that loads the parent and stashes it on `g`.

### CLI Commands & Scheduled Jobs

- Define Flask CLI commands with `click` and the `@with_appcontext` decorator; register them on `app.cli` inside `create_app()`.
- Scheduler job functions live in `src/services/scheduler.py` and follow the pattern `def job_name(): with scheduler.app.app_context(): ...` so the call has a real Flask + DB context.
- Each job owns its own session lifetime: `try` the body, `db.session.rollback()` on error, `db.session.remove()` in `finally`.

### Tests

- Use `pytest.mark.parametrize` for table-driven cases rather than per-case test functions.
- Reach for `pytest-mock` (`mocker.patch`) over `unittest.mock.patch` when the test does not need to assert on call counts — `mocker` cleans up automatically.
- Property-test pure functions (`utils/rule37.py`, `utils/transform.py`) with `hypothesis`. Do not property-test code that touches the database or the network.

## Frontend Rules (Vue / TypeScript)

- **Basics:** Use TypeScript, `<script setup lang="ts">`, and prefer DaisyUI over custom CSS.
- **Layouts:** Prefer `flex` or `grid` layout combined with `gap-*` utilities.
- **Inline Typing:** Avoid declaring detached `interface` or `type` blocks for local component structures. Define types inline directly where they are used (props, grouped refs, computed properties, etc.) unless the schema is explicitly shared across multiple files.
- **State Grouping:** Prefer `ref` over `reactive`. Group related parameters into unified object `ref`s by context (e.g., fields, filters, or UI interaction states like loading and modals).
- **Functions & Requests:** Use **named functions** for component-level methods and root handlers. Use **arrow functions** strictly for inline handlers, callbacks, and promise chains (`.then().catch()`). Use `.then().catch()` promise chains over `await` expressions. The `async` keyword on a function that never uses `await` is permitted.
- **Flash Messages**: Prefer the server-flashed toast (prop shared by Inertia on every response) and route it into `vue-toast-notification`. Only hardcode toast messages in `onSuccess` / `onError` when there is a concrete reason (e.g., fallback when the server did not flash anything).
- **Component Naming:** Shared components should be named for what they are (`LineChart`, `DateTimePicker`), not who first used them. Avoid domain-specific prefixes on generic components.
- **Wrapper Component Props:** When wrapping a third-party library (Chart.js, AirDatepicker, etc.), consider accepting a library-native options/config prop that the consumer spreads over component defaults. Avoid cherry-picking individual library knobs as separate props.

### Compliant Component Architecture Example

```vue
<script setup lang="ts">
import { ref } from 'vue'

// 1. Inline Typed Props
defineProps<{ title: string }>()

// 2. Contextually Grouped Object Refs with Inline Typing
const form = ref<{
    name: string
    email: string
}>({
    name: '',
    email: ''
})

const ui = ref<{
    loading: boolean
    showConfirmModal: boolean
}>({
    loading: false,
    showConfirmModal: false
})

// 3. Named Function for Component Method
function submitData() {
    ui.value.loading = true

    // 4. Promise Chain with Arrow Functions
    axios.post($route('api.users.store'), form.value)
        .then((response) => {
            useToast().success(response.data.message)
        })
        .catch((error) => {
            useToast().error(error.message)
        })
}
</script>

<template>
  <button @click="() => ui.showConfirmModal = true">Open</button>
  <button @click="submitData">Submit</button>
</template>
```

## API Response Contract

All API endpoints mounted under `src/routes/api/` (served at `/api/...`) **must** adhere to this envelope. This does **not** apply to page views under `src/routes/pages/` (served by Inertia).

### 1. HTTP Status as Source of Truth

No `"success": true/false` payload flag. The HTTP status dictates outcome: handle `2xx` in the success path and route `4xx/5xx` to the error path. With native `fetch`, check `response.ok` and throw or otherwise route non-2xx responses explicitly.

### 2. Envelope Schema (TypeScript Definition)

```typescript
interface ApiResponse<T = unknown> {
    message: string | null // Context summary (null on standard reads)
    data: T | null // Main payload — object, array, or null
    errors?: Record<string, string[]> // Present ONLY on 422 validation failures
}
```

### 3. Execution Behaviors

- **Successful Reads (`200 OK`):** `message` is `null`; `data` contains the requested resource object or collection array.
- **Mutative Actions (`200 OK` / `201 Created`):** For state switches, updates, or deletions where no entity structure is expected by the client, `data` is `null` and `message` contains clear success text.
- **Validation Failures (`422 Unprocessable Entity`):** `data` is `null`, `message` summarises the failure, and `errors` is a per-field dictionary. Flask does not auto-emit this envelope — wire it up with an `@app.errorhandler(ValidationError)` (or equivalent) before exposing a new write endpoint.
- **Application Exceptions (`4xx` / `5xx`):** `data` is `null`, and `message` contains the error summary context.

> Existing endpoints that still emit a `success` flag are grandfathered — do not add `success` to new endpoints; migrating existing emitters is a dedicated pass, not incidental work.

### 3. Frontend Interop

- The JSON provider (`CamelCaseJSONProvider` in `src/utils/transform.py`) emits all top-level and nested keys in `camelCase`, so a column named `latest_converted_fare` is delivered to the Vue layer as `latestConvertedFare`.
- Frontend code should branch on the HTTP status code (`.then` for 2xx, `.catch` for 4xx/5xx) and read `response.data.message` for the user-facing toast.
