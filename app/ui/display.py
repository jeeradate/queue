"""Full-screen wall display for a single counter (e.g. a TV in the corridor)."""

from __future__ import annotations

from nicegui import background_tasks, ui

from ..bootstrap import get_service
from ..services.realtime import hub
from .patient import _safe_color, _shade


@ui.page("/display/{counter_id}", title="MediQueue — Display")
async def display_page(counter_id: int) -> None:
    ui.query("body").classes("mq-display-body")
    service = get_service()

    @ui.refreshable
    def screen() -> None:
        snapshot = service.queue_snapshot(counter_id)
        if snapshot is None:
            with ui.element("div").classes("mq-display"):
                ui.label("Counter not found").style("font-size:2rem;font-weight:800")
                ui.label(f"Counter #{counter_id} does not exist.").classes("mq-display-caption")
            return

        layout = snapshot.layout
        accent = _safe_color(layout.accent_color)
        with ui.element("div").classes("mq-display").style(
            "background: radial-gradient(circle at 50% 15%, "
            f"{accent} 0%, #0b1220 72%)"
        ):
            ui.label(
                f"#{snapshot.counter.number} · {snapshot.counter.label or 'Counter'}"
            ).style("font-size:1.4rem;font-weight:700;opacity:.9")
            ui.label("Now serving").classes("mq-display-caption")
            ui.label(
                snapshot.serving.display_number if snapshot.serving else "—"
            ).classes("mq-number")
            if snapshot.serving is None:
                ui.label("Please wait for the next call").classes("mq-display-caption")
            if layout.show_next and snapshot.waiting:
                with ui.element("div").classes("mq-display-next"):
                    ui.label("Next").classes("mq-display-caption").style("opacity:.8")
                    for ticket in snapshot.waiting[:5]:
                        ui.label(f"#{ticket.display_number}").classes("mq-chip")
            if layout.show_waiting:
                ui.label(f"{snapshot.waiting_count} waiting").classes(
                    "mq-display-caption"
                ).style("opacity:.55")
            if layout.show_message and layout.message.strip():
                ui.label(layout.message).style(
                    "font-size:1.15rem;opacity:.85;max-width:900px"
                )

    with ui.element("div"):
        screen()

    notifications = hub.subscribe()

    async def listen() -> None:
        try:
            while True:
                await notifications.get()
                screen.refresh()
        finally:
            hub.unsubscribe(notifications)

    task = background_tasks.create(listen(), name=f"mediqueue-display-{counter_id}")
    ui.context.client.on_disconnect(
        lambda: (task.cancel(), hub.unsubscribe(notifications))
    )
