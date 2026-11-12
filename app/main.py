"""MediQueue entry point: bootstrap, register HTTP/PWA routes and run NiceGUI."""

from __future__ import annotations

from fastapi.responses import FileResponse, JSONResponse
from nicegui import app, ui

from .bootstrap import bootstrap
from .config import STATIC_DIR, settings

# Import page modules so their @ui.page decorators are registered.
from .ui import admin as _admin  # noqa: E402,F401
from .ui import auth as _auth  # noqa: E402,F401
from .ui import display as _display  # noqa: E402,F401
from .ui import patient as _patient  # noqa: E402,F401
from .ui import staff as _staff  # noqa: E402,F401
from .ui.theme import install_head  # noqa: E402


def register_http_routes() -> None:
    """Static assets, service worker scope and a health probe."""
    app.add_static_files("/static", STATIC_DIR)

    @app.get("/sw.js", include_in_schema=False)
    async def service_worker() -> FileResponse:
        # Service workers must be served from the root to control the whole app.
        return FileResponse(
            STATIC_DIR / "sw.js",
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/"},
        )

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> JSONResponse:
        return JSONResponse({"status": "ok", "app": "mediqueue"})


def main() -> None:
    bootstrap()
    install_head()
    register_http_routes()
    ui.run(
        host=settings.host,
        port=settings.port,
        title="MediQueue",
        favicon=str(STATIC_DIR / "icons" / "icon-192.png"),
        dark=False,
        show=False,
        reload=False,
        storage_secret=settings.storage_secret,
        session_middleware_kwargs={"max_age": settings.session_max_age},
        uvicorn_logging_level="info",
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
