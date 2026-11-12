"""Application settings loaded from environment variables (and an optional .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"

try:  # python-dotenv ships with NiceGUI; keep it optional for bare installs.
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:  # pragma: no cover - optional dependency
    pass


def _env(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable runtime configuration."""

    host: str
    port: int
    storage_secret: str
    database_url: str
    admin_pin: str
    staff_pin: str
    seed_defaults: bool
    session_max_age: int


settings = Settings(
    host=_env("MEDIQUEUE_HOST", "0.0.0.0"),
    port=_env_int("MEDIQUEUE_PORT", 8080),
    storage_secret=_env("MEDIQUEUE_STORAGE_SECRET", "change-me-mediqueue-secret"),
    database_url=_env(
        "MEDIQUEUE_DATABASE_URL",
        f"sqlite:///{(DATA_DIR / 'mediqueue.db').as_posix()}",
    ),
    admin_pin=_env("MEDIQUEUE_ADMIN_PIN", "1234"),
    staff_pin=_env("MEDIQUEUE_STAFF_PIN", "5678"),
    seed_defaults=_env_bool("MEDIQUEUE_SEED_DEFAULTS", True),
    session_max_age=_env_int("MEDIQUEUE_SESSION_MAX_AGE", 60 * 60 * 24 * 365),
)
