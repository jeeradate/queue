# AGENTS.md — MediQueue

Guidance for AI coding agents working on this repository. Human setup and
deployment docs live in `README.md`.

## Project

MediQueue is a hospital queue management PWA built with **NiceGUI 4** (server
driven UI over WebSocket), **SQLModel** (SQLite by default, PostgreSQL via URL),
and **uv** for dependency management. Python >= 3.11 (dev venv uses 3.14).

## Commands

```bash
uv sync                 # install/update dependencies
uv run mediqueue        # run the app (http://127.0.0.1:8080)
uv run pytest -q        # run the test suite
uv run python -m compileall -q app tests
```

Regenerate PWA icons (Windows only):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\generate_icons.ps1
```

Never start the server with `reload=True` for testing: the realtime hub is
in-process.

## Architecture

```
app/main.py        entry point: bootstrap, HTTP routes, ui.run
app/bootstrap.py   engine/service singletons + seed defaults
app/config.py      env-driven Settings (dataclass, frozen)
app/database.py    engine creation + SQLModel.metadata.create_all
app/models.py      Counter, Ticket, TicketStatus, DisplayLayout (pydantic)
app/services/
  queue_service.py queue business logic; every method owns its transaction
  realtime.py      RealtimeHub: in-process async pub/sub -> page refresh
app/ui/
  theme.py         PWA head, global CSS, shared header
  session.py       PIN auth, roles in app.storage.user, require() guard
  auth.py          /login, /logout
  patient.py       /              public patient tracker
  display.py       /display/{id}  full-screen wall display
  staff.py         /staff
  admin.py         /admin
static/            manifest, sw.js (served at /sw.js), offline.html, icons
tests/             pytest suite for the domain service
```

Data flow for live updates: a mutation calls `hub.publish()`; each page has one
background task from `background_tasks.create()` that awaits its subscription
queue and calls `refreshable.refresh()`. Unsubscribe and cancel the task in
`ui.context.client.on_disconnect`.

## Conventions

- Use `from __future__ import annotations` and full type hints on every function.
- Keep DB work inside `QueueService`; pages never open a SQLModel session.
- Every service mutation commits its own transaction and returns plain data or
  SQLModel objects (sessions use `expire_on_commit=False`).
- Store all datetimes in UTC (`utcnow()`); convert with `.astimezone()` only at
  the presentation layer.
- UI modules must be imported in `app/main.py` so their `@ui.page` decorators
  register.
- Keep styling in `app/ui/theme.py` CSS classes (`mq-*`) instead of inline styles
  where possible.
- Titles/labels are English; keep wording short and mobile-friendly.

## NiceGUI 4 notes (verified for this repo)

- `ui.run(..., storage_secret=..., session_middleware_kwargs={'max_age': ...})`
- `app.storage.user` is writable server-side and persists across restarts;
  `app.storage.browser` is read-only after the response is sent.
- Page guards use `ui.navigate.to('/login?next_url=...')`; there is no
  `RedirectResponse` return from page builders.
- Static files are mounted via `app.add_static_files`; the service worker is a
  FastAPI route at `/sw.js` with `Service-Worker-Allowed: /`.
- `ui.refreshable` functions are refreshed by name from background tasks.

## Security and deployment constraints

- Auth is PIN-based (constant-time compare). Do not invent per-user accounts
  without discussing it first.
- Session data and secrets come from environment variables; never commit `.env`.
- Run exactly one worker per database because `RealtimeHub` is in-process. For
  multiple workers, replace it with Redis pub/sub.
- PWA installation requires HTTPS outside localhost.
- Do not commit `data/`, `.nicegui/`, or generated databases.

## Testing

- Tests use a temporary SQLite file per test (`tmp_path`) via `init_database`.
- Add domain tests for any change in `queue_service.py`.
- UI changes should at least be smoke-tested over HTTP and, when realtime is
  involved, verified in a browser: mutate as staff and confirm the patient and
  display pages update without a reload.
