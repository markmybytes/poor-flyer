# AGENTS.md

**BEFORE ANY CODE CHANGES: Read [STYLE.md](STYLE.md) entirely.**
It defines blueprint placement, API contract, Vue patterns, naming, and verification requirements. Skipping it will cause violations.

This repo is a Flask 3 + Vue 3 (Inertia SPA) flight-price tracker that scrapes airline fares daily and emails buy-signal alerts based on the 37 % rule.

## Verification Order

Auto-fix first, then check for what remains. Run from the repo root.

| Scope                | Auto-fix                                                | Verify                                                |
| -------------------- | ------------------------------------------------------- | ----------------------------------------------------- |
| Backend (Python)     | `uv run ruff format .`                                  | `uv run ruff check .` then `uv run pytest`            |
| Migrations (model)   | —                                                       | `uv run flask db migrate` (review + rename) then `uv run flask db upgrade` |
| Frontend (Vue/TS)    | `npm run format` and `npx eslint src/frontend --fix`    | `npm run lint`                                        |
| Frontend types/tests | —                                                       | `npm run type-check` / `npm run test`                 |
| Bundling/runtime     | —                                                       | `npm run build`                                       |

Notes:

- `uv run` uses the lockfile interpreter; never invoke `python` / `pip` directly.
- `npm run lint` is `prettier --check` + `eslint`; there is no `lint:fix` script — pass `--fix` to eslint explicitly.
- `flask db migrate` only generates a revision; it does not apply it. `flask db upgrade` applies, `flask db downgrade` reverts.

## Architecture

- **Application factory** → `create_app()` in [`src/__init__.py`](src/__init__.py). Entry point for WSGI: [`wsgi.py`](wsgi.py) (`wsgi:app`).
- **Extensions** → [`src/extensions/`](src/extensions/). Heavy extensions live in their own module: `database.py` (Flask-SQLAlchemy + `db`), `cache.py` (Flask-Caching), `scheduler.py` (Flask-APScheduler). Lightweight singletons (`inertia`, `migrate`) and the `init_extensions(app)` entry point live in `__init__.py`.
- **Web routes (Inertia pages)** → [`src/routes/pages/`](src/routes/pages/). Registered under the `pages_bp` blueprint with no URL prefix; views return `render_inertia(...)` responses. Page props are `camelCase` (see CamelCaseJSONProvider).
- **API routes (JSON)** → [`src/routes/api/`](src/routes/api/). Registered under `api_bp` with `url_prefix='/api'`. Each view returns the envelope contract (see STYLE.md). Page views and API views are **separate** — do not mix `render_inertia` with envelope returns in the same view.
- **Services** → [`src/services/`](src/services/). Domain logic and integrations (scraper, fx_rates, scheduler jobs, setting, logs).
- **Utils** → [`src/utils/`](src/utils/). Pure helpers (transform, email, rule37).
- **Models** → defined in [`src/extensions/database.py`](src/extensions/database.py) on the shared `Base` / `db` instance. There is no `models/` package — to add a model, append a class to that file using SQLAlchemy 2 `Mapped[T]` style, then run `flask db migrate` and `flask db upgrade`.
- **Migrations** → [`migrations/`](migrations/) (Alembic via flask-migrate). Revision files in `migrations/versions/`.
- **Templates** → [`src/templates/`](src/templates/). Jinja base template (`base.html`) and email templates. The Inertia base template is what exposes `window.reverseUrl` to the frontend.
- **Frontend** → [`src/frontend/`](src/frontend/): `Pages/`, `Components/`, `Layouts/`, `css/`, `utils/`, `types.ts`, `route-plugin.d.ts`, `main.ts`, `bootstrap.ts`. Built by Vite into `src/static/dist/`.
- **Route surface**:
  - Pages: `/` redirects to `/itineraries/`; `/itineraries/`, `/itineraries/create`, `/itineraries/<id>`, `/logs`, `/settings`.
  - API: `/api/itineraries/` (CRUD + `/<id>/scrape`), `/api/settings/` (+ `/fx-rates/refresh`, `/test-email`), `/api/logs/` (DELETE).
- **Background jobs** → `flask-apscheduler` jobs declared in `app.config['JOBS']` (see `create_app`). Each job wraps its body in `with scheduler.app.app_context():` so it has a real Flask + DB context — see STYLE.md for the per-job session lifetime rules. Jobs run in a dedicated process via `flask run-scheduler`, never in the web worker.

## Testing

- **Python**: pytest 9 — [`tests/backend/`](tests/backend/). Fixtures defined in [`tests/backend/conftest.py`](tests/backend/conftest.py): session-scoped `app` (in-memory SQLite, `JOBS=[]`), per-test `clean_db` (truncates every table + clears cache).
- **JS**: Vitest with jsdom — [`tests/frontend/`](tests/frontend/). `$route` and `$inertia` are available as Vue globals (typed by `src/frontend/route-plugin.d.ts`; `window.reverseUrl` is provided by the Jinja base template, so mocks must set it in `beforeEach`).
- **Test DB**: `sqlite:///:memory:` set via `PF_DATABASE_URL` in conftest. No external database service is required.
- **Property tests**: `hypothesis` is available in the dev extras; use it for pure utilities (e.g. `utils/rule37.py`, `utils/transform.py`).
- CI runs both test suites on PRs to `main`.

## Constraints

- Do not edit `.github/workflows/**` without explicit instruction.
- Do not edit `src/static/dist/**`, `node_modules/**`, `.venv/**`, or `__pycache__/**`. Do not edit `migrations/versions/*.py` to "fix" history — write a new revision.
- Do not commit secrets, real SMTP credentials, or local `.env` values. Mask secrets before persisting them in the `config` table (see `src/services/setting.py:get_all_masked`).
- Do not commit `instance/app.log` or other runtime files under `instance/`.
- Do not bypass the application factory; tests and CLI commands must go through `create_app()` so `app.config` and extensions are initialised.
- Do not run the scheduler inside the web process — it lives in its own service (see `s6-overlay/s6-rc.d/`).

## Documentation

When you add, remove, or rename a module, blueprint, CLI command, route, scheduled job, dependency, or public API, update [README.md](README.md), [STYLE.md](STYLE.md), or this file as applicable.

## Environment

- **Python 3.12** via [uv](https://docs.astral.sh/uv/). Lockfile: `uv.lock`. Install dev deps: `uv sync --all-extras`. Never invoke `pip` directly in this repo.
- **Node 24** via [Volta](https://volta.sh/) (declared in `package.json`). Install: `npm install`.
- **Database**: SQLite by default (file under `instance/db.sqlite`); overridable via `PF_DATABASE_URL`.
- **Local dev command**: `flask dev` runs Vite, the Flask debug server, and the scheduler concurrently. Individual processes are also exposed as `flask run` and `flask run-scheduler`.
- **Frontend tooling**: Tailwind v4 + DaisyUI 5 configured inline in [`src/frontend/css/app.css`](src/frontend/css/app.css). There is no `tailwind.config.*` file; theme tokens live in CSS.
- **Timezone**: per-request timezone is resolved into `g.tz` by the `before_request` hook in `create_app()`. Use `g.tz` rather than reading `TZ` directly inside views.
- **Container**: Dockerfile uses `python:3.12-slim` and `pip install` (not `uv`) — that is intentional for image size; do not "fix" it without approval.
