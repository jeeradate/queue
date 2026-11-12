"""Session helpers shared by pages.

Authentication state lives in ``app.storage.user`` (server-side, keyed by the
signed session cookie) so it survives page reloads and app restarts.
"""

from __future__ import annotations

import secrets
from typing import Literal

from nicegui import app, ui

from ..config import settings

Role = Literal["admin", "staff"]
VALID_ROLES: tuple[Role, ...] = ("admin", "staff")
ROLE_KEY = "role"


def current_role() -> Role | None:
    role = app.storage.user.get(ROLE_KEY)
    return role if role in VALID_ROLES else None


def login(role: Role, pin: str) -> bool:
    """Validate a PIN with a constant-time comparison."""
    expected = settings.admin_pin if role == "admin" else settings.staff_pin
    if secrets.compare_digest(pin or "", expected):
        app.storage.user[ROLE_KEY] = role
        return True
    return False


def logout() -> None:
    app.storage.user.pop(ROLE_KEY, None)


def require(role: Role) -> bool:
    """Redirect anonymous visitors to the login page. Returns True when allowed."""
    if current_role() == role:
        return True
    ui.navigate.to(f"/login?next_url=/{role}")
    return False
