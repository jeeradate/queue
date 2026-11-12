"""Login / logout pages."""

from __future__ import annotations

from nicegui import ui

from .session import Role, login, logout
from .theme import page_frame


def _destination(role: Role, next_url: str) -> str:
    """Only follow same-role redirects; otherwise go to the role's home page."""
    home = "/admin" if role == "admin" else "/staff"
    if next_url in ("/admin", "/staff") and next_url == home:
        return next_url
    return home


@ui.page("/login", title="MediQueue — Sign in")
def login_page(next_url: str = "/") -> None:
    page_frame()
    safe_next = next_url if next_url.startswith("/") and not next_url.startswith("//") else "/"

    with ui.column().classes("mq-shell"):
        with ui.card().classes("mq-card"):
            ui.label("Staff sign in").classes("mq-title")
            ui.label(
                "Choose your role and enter the PIN provided by your administrator."
            ).classes("mq-muted")
            role_toggle = ui.toggle(
                {"staff": "Staff", "admin": "Admin"}, value="staff"
            ).props("spread no-caps").classes("w-full")
            pin_input = (
                ui.input("PIN", password=True, password_toggle_button=True)
                .props("outlined")
                .classes("w-full")
            )
            error_label = ui.label("").classes("mq-error")

            def submit() -> None:
                selected = role_toggle.value
                if selected not in ("staff", "admin"):
                    selected = "staff"
                role: Role = selected  # type: ignore[assignment]
                if login(role, str(pin_input.value or "")):
                    ui.navigate.to(_destination(role, safe_next))
                else:
                    error_label.set_text("Invalid PIN. Please try again.")
                    pin_input.value = ""

            pin_input.on("keydown.enter", submit)
            ui.button("Sign in", icon="login", on_click=submit).props(
                "unelevated no-caps"
            ).classes("w-full").style("background: var(--mq-primary)")

        with ui.card().classes("mq-card"):
            ui.label("Patients do not need to sign in.").classes("mq-section-title")
            ui.label(
                "Open the live queue page, pick a counter and add it to your home screen."
            ).classes("mq-muted")
            ui.button(
                "Go to live queue",
                icon="open_in_new",
                on_click=lambda: ui.navigate.to("/"),
            ).props("outline no-caps").classes("w-full")


@ui.page("/logout")
def logout_page() -> None:
    logout()
    ui.navigate.to("/")
