# AGENTS.md

Flask 3 + Vue 3 (Inertia SPA) flight-price tracker. Scrapes airline fares daily.

**Read [STYLE.md](STYLE.md) entirely before any code change.** It owns blueprint placement, API contract, Vue patterns, naming, and code style. This file owns environment, commands, boundaries, and repo-level conventions — not style.

## Commands

Run from repo root. Auto-fix first, then verify what remains.

| Scope                | Auto-fix                                             | Verify                                                                     |
| -------------------- | ---------------------------------------------------- | -------------------------------------------------------------------------- |
| Backend (Python)     | `uv run ruff format .`                               | `uv run ruff check .` then `uv run pytest`                                 |
| Migrations (model)   | —                                                    | `uv run flask db migrate` (review + rename) then `uv run flask db upgrade` |
| Frontend (Vue/TS)    | `npm run format` and `npx eslint src/frontend --fix` | `npm run lint`                                                             |
| Frontend types/tests | —                                                    | `npm run type-check` / `npm run test`                                      |
| Bundling/runtime     | —                                                    | `npm run build`                                                            |

- `uv run` uses the lockfile interpreter; never invoke `python` / `pip` directly.
- `npm run lint` is `prettier --check` + `eslint`; there is no `lint:fix` script — pass `--fix` to eslint explicitly.
- `flask db migrate` only generates a revision; `flask db upgrade` applies, `flask db downgrade` reverts.

## Architecture

- **Entry**: `create_app()` in `src/__init__.py`; WSGI: `wsgi.py`.
- **Run**: `flask dev` (all-in-one) or `flask run` / `flask run-scheduler` (split).
- **Layout**: `src/routes/{pages,api}`, `services`, `utils`, `extensions`, `frontend`, `templates`; `migrations/`, `tests/`.
- Scheduler lives in its own service (see `s6-overlay/s6-rc.d/`), not the web process.

## Environment

- **Python 3.12** via [uv](https://docs.astral.sh/uv/). Lockfile: `uv.lock`. Install: `uv sync --all-extras`. Never `pip`.
- **Node** via [Volta](https://volta.sh/) (declared in `package.json`).
- **Database**: SQLite by default (`instance/db.sqlite`); overridable via `PF_DATABASE_URL`.
- **Frontend tooling**: Tailwind v4 + DaisyUI 5, configured inline in [`src/frontend/css/app.css`](src/frontend/css/app.css).
- **Timezone**: `g.tz` set by `before_request` in `create_app()`. Use `g.tz`, not `TZ`, inside views.
- **Container**: Dockerfile uses `python:3.12-slim` + `pip install` (not `uv`) — intentional for image size; do not "fix" without approval.

## Testing

- **Python**: pytest 9 — [`tests/backend/`](tests/backend/). Fixtures in [`tests/backend/conftest.py`](tests/backend/conftest.py): session-scoped `app` (in-memory SQLite, `JOBS=[]`), per-test `clean_db` (truncates every table + clears cache).
- **JS**: Vitest + jsdom — [`tests/frontend/`](tests/frontend/). `$route` and `$inertia` are Vue globals (typed by `src/frontend/route-plugin.d.ts`); `window.reverseUrl` is provided by the Jinja base template, so mocks must set it in `beforeEach`.
- **Test DB**: `sqlite:///:memory:` via `PF_DATABASE_URL` in conftest. No external DB service.
- **Property tests**: `hypothesis` available in dev extras; use for pure utilities (e.g. `utils/rule37.py`, `utils/transform.py`).
- CI runs both suites on PRs to `main`.

## Boundaries

### ✅ Always
- Go through `create_app()` for tests and CLI commands so `app.config` and extensions initialise.
- Run the relevant auto-fix + verify commands from the table above before declaring work done.
- Update [README.md](README.md), [STYLE.md](STYLE.md), or this file when adding/removing/renaming a module, blueprint, CLI command, route, scheduled job, dependency, or public API.

### ⚠️ Ask First
- Editing `.github/workflows/**`.
- Changing the Dockerfile's `pip install` (not `uv`) choice.
- Schema changes that are not portable to SQLite (may need split revisions).

### 🚫 Never
- Edit `src/static/dist/**`, `node_modules/**`, `.venv/**`, or `__pycache__/**`.
- Edit `migrations/versions/*.py` to "fix" history — write a new revision.
- Commit secrets, real SMTP credentials, or local `.env` values. Mask secrets before persisting in the `config` table (see `src/services/setting.py:get_all_masked`).
- Commit `instance/app.log` or other runtime files under `instance/`.
- Bypass the application factory.
- Run the scheduler inside the web process.
- Invoke `pip` / `python` directly — use `uv run`.
