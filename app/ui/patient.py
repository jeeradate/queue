"""Patient-facing live queue page (the installable PWA home screen)."""

from __future__ import annotations

from datetime import datetime

from nicegui import app, background_tasks, ui

from ..bootstrap import get_service
from ..services.realtime import hub
from .theme import page_frame

COUNTER_KEY = "patient_counter_id"
DEFAULT_ACCENT = "#0f766e"


def _safe_color(value: str) -> str:
    """Only accept #rrggbb values so the colour can be embedded in CSS safely."""
    color = (value or "").strip()
    if len(color) == 7 and color.startswith("#") and all(
        ch in "0123456789abcdefABCDEF" for ch in color[1:]
    ):
        return color
    return DEFAULT_ACCENT


def _shade(color: str, factor: float = 0.72) -> str:
    rgb = (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))
    return "#" + "".join(
        f"{max(0, min(255, int(channel * factor))):02x}" for channel in rgb
    )


def _restore_counter_id() -> int | None:
    saved = app.storage.user.get(COUNTER_KEY)
    if not isinstance(saved, int):
        return None
    counter = get_service().get_counter(saved)
    return saved if counter is not None and counter.active else None


@ui.page("/", title="MediQueue — Live queue")
async def patient_page() -> None:
    page_frame(active="patient")
    service = get_service()
    state: dict[str, int | None] = {"counter_id": _restore_counter_id()}
    counters = service.list_counters(active_only=True)
    options = {
        counter.id: f"#{counter.number} · {counter.label or 'Counter'}"
        for counter in counters
        if counter.id is not None
    }

    def stat(label: str, value: str | int) -> None:
        with ui.element("div").classes("mq-hero-stat"):
            ui.label(str(value)).style(
                "display:block;font-size:1.15rem;font-weight:800;"
                "font-variant-numeric:tabular-nums"
            )
            ui.label(label).style(
                "font-size:.66rem;opacity:.82;text-transform:uppercase;"
                "letter-spacing:.08em"
            )

    @ui.refreshable
    def dashboard() -> None:
        counter_id = state["counter_id"]
        if counter_id is None:
            with ui.card().classes("mq-card"):
                ui.label("Choose a counter to start tracking").classes("mq-section-title")
                ui.label(
                    "Pick the room or window printed on your ticket. "
                    "You can switch at any time."
                ).classes("mq-muted")
                for counter in counters:
                    if counter.id is None:
                        continue
                    ui.button(
                        f"#{counter.number} · {counter.label or 'Counter'}",
                        on_click=lambda _=None, cid=counter.id: select_counter(cid),
                    ).props("outline no-caps").classes("w-full justify-start").style(
                        "margin-top:8px"
                    )
            return

        snapshot = service.queue_snapshot(counter_id)
        if snapshot is None:
            state["counter_id"] = None
            app.storage.user.pop(COUNTER_KEY, None)
            with ui.card().classes("mq-card"):
                ui.label("This counter is no longer available.").classes("mq-section-title")
                ui.label("Please choose another counter from the list above.").classes("mq-muted")
            return

        layout = snapshot.layout
        accent = _safe_color(layout.accent_color)
        with ui.element("div").classes("mq-hero").style(
            f"background: linear-gradient(135deg, {accent} 0%, {_shade(accent)} 100%)"
        ):
            with ui.element("div").classes("mq-hero-top"):
                ui.label(
                    f"#{snapshot.counter.number} · "
                    f"{snapshot.counter.label or 'Counter'}"
                ).classes("mq-hero-label")
                ui.label("In service" if snapshot.serving else "Idle").classes("mq-pill")
            ui.label("Now serving").classes("mq-hero-caption")
            ui.label(
                snapshot.serving.display_number if snapshot.serving else "—"
            ).classes("mq-number")
            if snapshot.serving is None:
                ui.label("Waiting for the first call").classes("mq-hero-label").style(
                    "opacity:.85"
                )
            with ui.element("div").classes("mq-hero-stats"):
                if layout.show_waiting:
                    stat("Waiting", snapshot.waiting_count)
                if layout.show_eta:
                    stat("Est. wait", f"{snapshot.eta_minutes} min")
                stat("Completed", snapshot.done_count)

        if layout.show_message and layout.message.strip():
            ui.label(layout.message).classes("mq-message")

        with ui.card().classes("mq-card"):
            with ui.row().classes("w-full items-center"):
                ui.label("Queue status").classes("mq-section-title")
                ui.space()
                ui.label(f"{snapshot.waiting_count} waiting").classes("mq-muted")
            if not layout.show_next:
                ui.label("Live updates are on.").classes("mq-muted").style("margin-top:8px")
            elif snapshot.waiting:
                shown = snapshot.waiting[:5]
                with ui.row().classes("w-full items-center").style("margin-top:10px"):
                    ui.label("Next 5 in line").classes("mq-muted")
                    ui.space()
                    ui.label(f"showing {len(shown)}").classes("mq-muted")
                with ui.element("div").classes("mq-chips").style("margin-top:6px"):
                    for index, ticket in enumerate(shown):
                        classes = "mq-chip mq-chip-next" if index == 0 else "mq-chip"
                        ui.label(f"#{ticket.display_number}").classes(classes)
                if len(snapshot.waiting) > 5:
                    ui.label(
                        f"+{len(snapshot.waiting) - 5} more waiting"
                    ).classes("mq-muted").style("margin-top:6px")
            else:
                ui.label("No one is waiting — you are all caught up.").classes("mq-muted").style(
                    "margin-top:8px"
                )

        with ui.row().classes("w-full items-center justify-between"):
            ui.label(f"Updated {datetime.now().strftime('%H:%M:%S')}").classes("mq-muted")
            ui.button(
                "Refresh",
                icon="refresh",
                on_click=lambda: ui.run_javascript("window.location.reload()"),
            ).props("flat dense no-caps").classes("mq-muted")

    def select_counter(counter_id: int | None) -> None:
        state["counter_id"] = counter_id
        if counter_id is None:
            app.storage.user.pop(COUNTER_KEY, None)
        else:
            app.storage.user[COUNTER_KEY] = counter_id
        dashboard.refresh()

    with ui.column().classes("mq-shell"):
        with ui.column().style("gap:2px"):
            ui.label("Track your queue").classes("mq-title")
            ui.label(
                "Live updates from the hospital — no need to refresh."
            ).classes("mq-subtitle")

        with ui.card().classes("mq-card"):
            ui.select(
                options=options,
                value=state["counter_id"],
                label="Counter / screen",
                with_input=True,
                on_change=lambda event: select_counter(
                    int(event.value) if event.value is not None else None
                ),
            ).props("outlined dense options-dense").classes("w-full")
            ui.label("Your selection is remembered on this device.").classes(
                "mq-muted"
            ).style("margin-top:6px")

        dashboard()

        with ui.card().classes("mq-card"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("install_mobile").style("color: var(--mq-primary)")
                ui.label("Install as an app").classes("mq-section-title")
            ui.label(
                "Open your browser menu and choose “Add to Home screen” to keep "
                "MediQueue one tap away."
            ).classes("mq-muted").style("margin-top:4px")

    notifications = hub.subscribe()

    async def listen() -> None:
        try:
            while True:
                await notifications.get()
                dashboard.refresh()
        finally:
            hub.unsubscribe(notifications)

    task = background_tasks.create(listen(), name="mediqueue-patient")
    ui.context.client.on_disconnect(
        lambda: (task.cancel(), hub.unsubscribe(notifications))
    )
