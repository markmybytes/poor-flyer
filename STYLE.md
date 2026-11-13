# STYLE.md — Coding Style Guide

Conventions for humans and AI agents in poor-flyer.

## Rule Priority

1. Security and access control
2. Correctness and data integrity
3. Existing architecture and file placement
4. Simplicity and readability
5. Local consistency with nearby code

A higher rule wins a conflict. Ask when a requirement is ambiguous.

## Core Principles

- Solve the problem directly. Build no abstraction before a second caller exists.
- **YAGNI threshold.** Keep execution logic inline in its view, job, or handler until:
  1. **Reuse** — a second entry point (CLI command, scheduler job) needs the same logic.
  2. **Growth** — the block passes one readable screen (> 100 lines), or gains unrelated side effects (notifications, audit loops, cache clearing).
- No single-use helpers. No intermediate variables while the expression still reads.

## Naming

- Tables: plural `snake_case` (`fare_snapshots`).
- Columns: `snake_case`. `CamelCaseJSONProvider` (`src/utils/transform.py`) exposes them as `camelCase`; never rename a column for the frontend.
- Routes: `kebab-case` segments.
- Python modules, functions, variables: `snake_case`. Classes, Pydantic models, dataclasses, type aliases: `PascalCase`. Constants: `UPPER_SNAKE_CASE`.
- TypeScript functions, methods, variables: `camelCase`. Types, interfaces, component files: `PascalCase` (`PascalCase.vue`).

## Placement

- Build routes through blueprints. Never register a view on `app` directly.

| Content                                      | Location                     |
| -------------------------------------------- | ---------------------------- |
| Web (Inertia) views                          | `src/routes/pages/`          |
| API (JSON) views                             | `src/routes/api/`            |
| Services, domain logic                       | `src/services/`              |
| Pure helpers (no Flask globals, no I/O)      | `src/utils/`                 |
| Extension singletons, `init_extensions(app)` | `src/extensions/`            |
| SQLAlchemy models, shared `Base` / `db`      | `src/extensions/database.py` |
| Pages                                        | `src/frontend/Pages/`        |
| Shared components                            | `src/frontend/Components/`   |
| Layouts                                      | `src/frontend/Layouts/`      |

- Keep views thin. Move non-trivial business logic to a service.
- Scheduler jobs live in `src/services/scheduler.py`. Reusable workhorses (`scrape_prices`, `convert_amount`) stay in their owning service module.

## Python / Flask

- Type every public signature, return type included. Models use `Mapped[T]` / `Mapped[T | None]`.
- Add `from __future__ import annotations` where forward references or many string literals appear.
- Parameters take `collections.abc` types (`Mapping`, `Sequence`, `Iterable`). Returns take builtins (`list`, `dict`).
- Use `pathlib.Path`. No `os.path.join` in new code.
- Page views return `flask_inertia.render_inertia`. API views return the JSON envelope below.
- Read timezone from `flask.g.tz`, never from `os.environ['TZ']`.
- Read runtime config from `current_app.config[...]`. `os.getenv` only inside `create_app()`.

### Logging

- One module-level logger per file: `logging.getLogger(__name__)`. Never add handlers, set levels, or call `basicConfig` — `src/logging_config.py` owns them.
- Messages are one lowercase event plus `key=value` fields passed as arguments: `logger.info('scraped fares: itinerary_id=%s count=%d', id, n)`. `tests/backend/test_logging_conventions.py` enforces the shape.
- One log per handled failure, at the boundary that handles it. `ERROR` only when a human must act; expected conditions are `INFO` or `DEBUG`, and `logger.exception(...)` belongs inside the handler that catches.
- The correlation id is attached automatically; never format one into a message.

### Exceptions

- Catch the narrowest class that expresses the failure (`FXRatesError`, `KeyError`, `ValueError`). Bare `except Exception:` at module top level is allowed only when it immediately re-raises, converts to a 5xx envelope, or rolls back the session.
- Job bodies: `try` the work, `db.session.rollback()` on error, `db.session.remove()` in `finally`. Long-lived sessions leak identity-map state across iterations.
- Use `contextlib.suppress(SpecificError)` for tolerated failures.

### Status Fields

- New finite status fields use `enum.StrEnum` on a `String` column, so the column, the Python value, and the JSON output are one string and typos fail at import:

```python
class ScrapeStatus(StrEnum):
    SUCCESS = 'success'
    ERROR = 'error'


scrape_status: Mapped[ScrapeStatus] = mapped_column(String, default=ScrapeStatus.SUCCESS)
```

- `scrape_status`, `trip_type`, and `Phase` predate this rule and stay plain.

### I/O Fan-Out

- Bounded fan-out (N emails from one job) uses `ThreadPoolExecutor` with a small `max_workers`: it gives a context manager, deterministic shutdown, and `.result()`.
- `threading.Thread(daemon=True)` is for fire-and-forget notifications only.
- Never share a SQLAlchemy session across threads.

### Eager Loading

- Never lazy-load a collection inside a JSON-serialising view. Start from an explicit `select(...)`:

```python
stmt = (
    select(Itinerary)
    .options(selectinload(Itinerary.flights).selectinload(Flight.fare_snapshots))
    .order_by(Itinerary.created_at)
)
```

- `selectinload` for collections (`list[...]`). `joinedload` for single-row relationships (`ManyToOne`, `OneToOne`).
- End a chain that joins a collection with `.unique()` on the parent.
- Declare every serialised relationship in the same `options(...)` as the parent. Never rely on implicit `lazy='select'`.

### Cache Keys

- Application keys: `<domain>:<purpose>[:<scope-or-variant>...]:v<schema>` — lowercase, colon-separated, stable order, schema version last. Hash long or sensitive identifiers. Bump to `v2` only when the cached shape changes.
- Package-managed keys keep their package-defined names.

### Migrations

- Every revision has a working `downgrade()` mirroring the upgrade.
- Additive columns: `nullable=True` plus a `server_default`, so the upgrade does not block on populated tables.
- SQLite runs in batch mode (`render_as_batch=True`). A type change that is not portable to SQLite still needs two revisions — check first.
- Never edit a merged revision; write a new one.
- After a model edit: `uv run flask db migrate`, review the autogenerated diff, rename the revision, then `uv run flask db upgrade`.

## Blueprints and Routes

A view parses the request, authorises and validates, delegates, and returns the right shape. Formatting and short loops stay inline under the YAGNI threshold.

### Splitting Files

Start a new blueprint or module when one of these holds:

- **Context isolation** — public flows and internal admin flows need different role checks; one file makes every query carry both.
- **Pivot attributes** — a child relationship has its own mutable parameters that clutter the parent resource.
- **Cohesion** — the models or view modules are unrelated.

### Inertia First, JSON by Exception

Inertia is the default for page reads, forms, CRUD, redirects, and mutations. API routes are for interactions that must avoid an Inertia visit: polling, job status, data queries, isolated state updates (status toggle, inline sort). Never for an ordinary form submission.

- Use native `fetch` and check `response.ok` — `fetch` does not reject on 4xx/5xx.
- Apply the returned state in the success path, so the UI matches the database (frontend sync tax).
- On-demand background actions (a fare scrape) are an API endpoint under `src/routes/api/`, mounted on `api_bp` with the envelope, applied by the component inside `.then`.
- Group related actions for one model in a single blueprint with semantic endpoint names:

```python
# src/routes/api/itinerary.py
itineraries_bp = Blueprint('itineraries', __name__, url_prefix='/itineraries')


@itineraries_bp.patch('/<itinerary_id>/status')
def update_status(itinerary_id: str): ...


@itineraries_bp.patch('/<itinerary_id>/ordering')
def update_sort_order(itinerary_id: str): ...
```

- Form CRUD posts to the URL that renders the form (`POST /itineraries`, `POST /settings`) via `router.post`, so validation errors return in the Inertia error bag.

### Nested Route Ownership

Express ownership in the route, business rules in the view.

```python
# Ownership in the URL prefix and a scoped query.
@itineraries_bp.route('/<itinerary_id>/packages', ...)
def packages_index(itinerary_id: str): ...
```

- Guard with the query, not a later comparison:

```python
package = db.session.execute(
    select(Package).where(Package.id == pkg_id, Package.itinerary_id == itinerary_id)
).scalar_one_or_none()
```

- A heavy or cross-resource parent check goes in a `before_request` on the nested blueprint, which loads the parent onto `g`.

## CLI and Scheduled Jobs

- CLI commands use `click` with `@with_appcontext`, registered on `app.cli` inside `create_app()`.
- Jobs live in `src/services/scheduler.py` as `def job_name():` wrapping `with scheduler.app.app_context():`, and own their session lifetime (see Exceptions).
- Run exactly one scheduler process: the trigger lives in process memory, so two instances fire each job twice.

## Tests

- `pytest.mark.parametrize` for table-driven cases, not one function per case.
- `mocker.patch` over `unittest.mock.patch`, unless the test asserts on call counts.
- Property-test pure functions (`utils/rule37.py`, `utils/transform.py`) with `hypothesis`. Never database or network code.

## Vue / TypeScript

- TypeScript, `<script setup lang="ts">`. DaisyUI before custom CSS.
- Lay out with `flex` or `grid` plus `gap-*`.
- Type component-local shapes inline at the point of use (props, grouped refs, computed). A shared `interface` only when several files need it.
- Prefer `ref` over `reactive`. Group related values into one object `ref` per context (fields, filters, UI state).
- Named functions for component methods and root handlers. Arrow functions for inline handlers, callbacks, and `.then()` chains.
- Prefer `.then().catch()` over `await`. An `async` function that never awaits is allowed.
- Toast messages come from the server flash (prop shared by Inertia). Hardcode one in `onSuccess` / `onError` only with a reason, such as a fallback when nothing was flashed.
- Name a shared component for what it is (`LineChart`, `DateTimePicker`), never for its first user. No domain prefixes on generic components.
- Wrapping a third-party library: accept a library-native options prop to spread over defaults, not one prop per knob.

### Responsive Breakpoints

Use Tailwind's default breakpoints. No `--breakpoint-*` overrides, no arbitrary variants. Write mobile-first: unqualified classes are the `< sm` tier.

Three layout tiers, changed at two breakpoints:

- `< sm` — mobile.
- `sm` to `xl` — tablet. Too wide for one design, so `md` and `lg` are allowed inside it.
- `>= xl` — desktop.

`md` and `lg` adjust density, sizes, and spacing. They never introduce a layout. Structure changes at `sm` and `xl` only.

- The content container caps at `xl` (`max-w-7xl`), so growth stops with structure.
- Gaps and card padding stop increasing at `lg`.
- Forms: one column below `md` — the one place `md` carries structure.
- Type follows the box: when a breakpoint narrows a box, step the type down there.
- Check both sides of every breakpoint you use.

## API Response Contract

Every endpoint under `src/routes/api/` (`/api/...`) returns this envelope. Page views under `src/routes/pages/` do not.

### Status Is the Outcome

No `"success"` flag. `2xx` is success, `4xx`/`5xx` is failure. With `fetch`, check `response.ok` and route the rest to the error path.

### Envelope

```typescript
interface ApiResponse<T = unknown> {
  message: string | null // context summary; null on a plain read
  data: T | null // payload: object, array, or null
  errors?: Record<string, string[]> // only on 422
}
```

### Behaviour

- **Read (`200`)** — `message: null`, `data` holds the resource or collection.
- **Mutation (`200` / `201`)** — `data: null`, `message` holds the success text, when the client expects no entity back.
- **Validation failure (`422`)** — `data: null`, `message` summarises, `errors` maps field to messages. Flask does not emit this by itself: wire `@app.errorhandler(ValidationError)` before exposing a write endpoint.
- **Application error (`4xx` / `5xx`)** — `data: null`, `message` carries the summary.

Endpoints that still emit `success` are grandfathered. Never add the flag to a new endpoint; migrating the old ones is a dedicated pass.

### Frontend

- The JSON provider emits every key, nested included, in `camelCase`: `latest_converted_fare` arrives as `latestConvertedFare`.
- Branch on status (`.then` for 2xx, `.catch` for the rest) and toast `response.data.message`.
