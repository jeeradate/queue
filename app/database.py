"""Database engine setup and schema creation."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlmodel import SQLModel, create_engine

from . import models  # noqa: F401  (import registers tables with SQLModel.metadata)


def _ensure_sqlite_directory(url: str) -> None:
    """Create the parent directory for a file-based SQLite database."""
    database = make_url(url).database
    if not database or database == ":memory:":
        return
    path = Path(database)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)


def _apply_light_migrations(engine: Engine) -> None:
    """Additive, backward-compatible schema updates for existing databases.

    ``SQLModel.metadata.create_all`` only creates missing tables; it never alters
    an existing one. Adding the optional alphanumeric ticket code is therefore
    handled explicitly so live queue data is preserved.
    """
    inspector = inspect(engine)
    if "tickets" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("tickets")}
    if "code" in columns:
        return
    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE tickets ADD COLUMN code VARCHAR(20) NOT NULL DEFAULT ''")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_tickets_code ON tickets (code)")
        )


def init_database(url: str) -> Engine:
    """Create the engine, make sure every table exists and apply safe upgrades."""
    sqlite = url.startswith("sqlite")
    if sqlite:
        _ensure_sqlite_directory(url)
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False} if sqlite else {},
        pool_pre_ping=True,
    )
    SQLModel.metadata.create_all(engine)
    _apply_light_migrations(engine)
    return engine
