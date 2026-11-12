"""Application bootstrap: engine, service and seed data singletons."""

from __future__ import annotations

from sqlalchemy.engine import Engine

from .config import settings
from .database import init_database
from .services.queue_service import QueueService

_engine: Engine | None = None
_service: QueueService | None = None


def bootstrap() -> QueueService:
    """Initialise the database once and return the shared queue service."""
    global _engine, _service
    if _service is not None:
        return _service
    _engine = init_database(settings.database_url)
    _service = QueueService(_engine)
    if settings.seed_defaults:
        _service.seed_defaults()
    return _service


def get_service() -> QueueService:
    if _service is None:
        raise RuntimeError("MediQueue is not bootstrapped; call bootstrap() first")
    return _service


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("MediQueue is not bootstrapped; call bootstrap() first")
    return _engine
