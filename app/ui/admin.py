"""Admin console: counters, display layouts and live overview."""

from __future__ import annotations

from pydantic import ValidationError
from nicegui import background_tasks, ui

from ..bootstrap import get_service
from ..models import DisplayLayout
from ..services.realtime import hub
from .session import require
from .theme import page_frame


def _mini_stat(label: str, value: str | int) -> None:
    with ui.element("div").classes("mq-mini-stat"):
        ui.label(str(value)).style(
            "display:block;font-size:1.4rem;font-weight:800;"
            "font-variant-numeric:tabular-nums"
        )
        ui.label(label).classes("mq-muted")


@ui.page("/admin", title="MediQueue — Administration")
async def admin_page() -> None:
    if not require("admin"):
        return
    page_frame(active="admin")
    service = get_service()

    summaries = service.counter_summaries()
    max_number = max((summary.counter.number for summary in summaries), default=0)

    editing: dict[str, int | None] = {"counter_id": None}
    deleting: dict[str, int | None] = {"counter_id": None}

    def publish_refresh() -> None:
        hub.publish()

    # -- edit dialog -----------------------------------------------------
    with ui.dialog() as edit_dialog, ui.card().classes("mq-dialog"):
        ui.label("Edit counter").classes("mq-section-title")
        edit_number = (
            ui.number("Counter number", min=1, precision=0)
            .props("outlined dense")
            .classes("w-full")
        )
        edit_label = ui.input("Label").props("outlined dense").classes("w-full")
        edit_active = ui.switch("Active", value=True)
        ui.separator()
        ui.label("Display layout").classes("mq-section-title")
        edit_show_next = ui.switch("Show next numbers", value=True)
        edit_show_waiting = ui.switch("Show waiting count", value=True)
        edit_show_eta = ui.switch("Show estimated wait", value=True)
        edit_show_message = ui.switch("Show custom message", value=True)
        edit_message = (
            ui.input("Message", placeholder="Please have your ticket ready.")
            .props("outlined dense")
            .classes("w-full")
        )
        edit_accent = (
            ui.input("Accent color", placeholder="#0f766e")
            .props("outlined dense")
            .classes("w-full")
        )
        edit_avg = (
            ui.number(
                "Average service minutes", min=1, max=120, precision=0, value=5
            )
            .props("outlined dense")
            .classes("w-full")
        )
        edit_error = ui.label("").classes("mq-error")
        with ui.row().classes("w-full justify-end"):
            ui.button("Cancel", on_click=edit_dialog.close).props("flat no-caps")
            ui.button("Save", on_click=lambda: save_edit()).props(
                "unelevated no-caps"
            ).style("background: var(--mq-primary)")

    def open_edit(counter_id: int) -> None:
        counter = service.get_counter(counter_id)
        if counter is None:
            ui.notify("Counter no longer exists.", type="negative")
            return
        layout = counter.display_layout()
        editing["counter_id"] = counter_id
        edit_number.value = counter.number
        edit_label.value = counter.label
        edit_active.value = counter.active
        edit_show_next.value = layout.show_next
        edit_show_waiting.value = layout.show_waiting
        edit_show_eta.value = layout.show_eta
        edit_show_message.value = layout.show_message
        edit_message.value = layout.message
        edit_accent.value = layout.accent_color
        edit_avg.value = layout.avg_service_minutes
        edit_error.set_text("")
        edit_dialog.open()

    def save_edit() -> None:
        counter_id = editing["counter_id"]
        if counter_id is None:
            return
        try:
            layout = DisplayLayout(
                show_next=bool(edit_show_next.value),
                show_waiting=bool(edit_show_waiting.value),
                show_eta=bool(edit_show_eta.value),
                show_message=bool(edit_show_message.value),
                message=str(edit_message.value or ""),
                accent_color=str(edit_accent.value or "").strip() or "#0f766e",
                avg_service_minutes=int(edit_avg.value or 5),
            )
            service.update_counter(
                counter_id,
                number=int(edit_number.value or 0) or None,
                label=str(edit_label.value or ""),
                active=bool(edit_active.value),
                layout=layout,
            )
        except (ValueError, ValidationError) as exc:
            edit_error.set_text(str(exc))
            return
        edit_dialog.close()
        ui.notify("Counter updated.", type="positive")
        publish_refresh()

    # -- delete dialog ---------------------------------------------------
    with ui.dialog() as delete_dialog, ui.card().classes("mq-dialog"):
        ui.label("Delete counter").classes("mq-section-title")
        delete_text = ui.label("").classes("mq-muted")
        ui.label(
            "All tickets for this counter will be permanently removed."
        ).classes("mq-muted")
        with ui.row().classes("w-full justify-end").style("margin-top:12px"):
            ui.button("Cancel", on_click=delete_dialog.close).props("flat no-caps")
            ui.button("Delete", on_click=lambda: confirm_delete()).props(
                "unelevated no-caps color=negative"
            )

    def open_delete(counter_id: int, label: str) -> None:
        deleting["counter_id"] = counter_id
        name = label or f"Counter {counter_id}"
        delete_text.set_text(f'Delete "{name}"?')
        delete_dialog.open()

    def confirm_delete() -> None:
        counter_id = deleting["counter_id"]
        if counter_id is not None:
            try:
                service.delete_counter(counter_id)
                ui.notify("Counter deleted.", type="warning")
            except ValueError as exc:
                ui.notify(str(exc), type="negative")
        delete_dialog.close()
        publish_refresh()

    # -- overview (live) -------------------------------------------------
    @ui.refreshable
    def overview() -> None:
        current = service.counter_summaries()
        total_waiting = sum(summary.waiting_count for summary in current)
        active_count = sum(1 for summary in current if summary.counter.active)
        serving_count = sum(
            1 for summary in current if summary.serving_number is not None
        )
        with ui.element("div").classes("mq-stat-row"):
            _mini_stat("Counters", len(current))
            _mini_stat("Active", active_count)
            _mini_stat("Waiting", total_waiting)
            _mini_stat("Serving", serving_count)

        with ui.card().classes("mq-card"):
            ui.label("Counters").classes("mq-section-title")
            if not current:
                ui.label("No counters yet — add one below.").classes("mq-muted").style(
                    "margin-top:8px"
                )
            for summary in current:
                counter = summary.counter
                with ui.row().classes("mq-queue-row w-full"):
                    ui.label(f"#{counter.number}").classes("mq-ticket")
                    with ui.column().style("gap:0"):
                        ui.label(counter.label or "Unnamed counter").style(
                            "font-weight:600"
                        )
                        bits = [f"{summary.waiting_count} waiting", f"{summary.done_count} done"]
                        if summary.serving_number is not None:
                            bits.insert(0, f"serving #{summary.serving_number}")
                        ui.label(" · ".join(bits)).classes("mq-muted")
                    ui.space()
                    ui.badge("active" if counter.active else "inactive").props(
                        "color=teal" if counter.active else "color=grey"
                    )
                    ui.button(
                        icon="edit",
                        on_click=lambda _=None, cid=counter.id: (
                            open_edit(cid) if cid is not None else None
                        ),
                    ).props("flat round dense").tooltip("Edit layout")
                    ui.button(
                        icon="delete",
                        on_click=lambda _=None, cid=counter.id, lbl=counter.label: (
                            open_delete(cid, lbl) if cid is not None else None
                        ),
                    ).props("flat round dense color=negative").tooltip("Delete")

    # -- add / total actions ---------------------------------------------
    def add_counter() -> None:
        try:
            counter = service.create_counter(
                number=int(add_number.value or 0),
                label=str(add_label.value or ""),
            )
        except ValueError as exc:
            ui.notify(str(exc), type="negative")
            return
        add_number.value = (counter.number or 0) + 1
        add_label.value = ""
        ui.notify(f"Counter #{counter.number} added.", type="positive")
        publish_refresh()

    def apply_total() -> None:
        try:
            created = service.ensure_total_counters(int(ensure_total.value or 0))
        except ValueError as exc:
            ui.notify(str(exc), type="negative")
            return
        if created:
            ui.notify(f"Created {len(created)} counter(s).", type="positive")
        else:
            ui.notify("No new counters were needed.", type="info")
        publish_refresh()

    with ui.column().classes("mq-shell mq-shell-wide"):
        with ui.column().style("gap:2px"):
            ui.label("Administration").classes("mq-title")
            ui.label(
                "Configure counters, display layouts and live behaviour."
            ).classes("mq-subtitle")

        overview()

        with ui.element("div").classes("mq-grid-2"):
            with ui.card().classes("mq-card"):
                ui.label("Add a counter").classes("mq-section-title")
                add_number = (
                    ui.number(
                        "Counter number", value=max_number + 1, min=1, precision=0
                    )
                    .props("outlined dense")
                    .classes("w-full")
                )
                add_label = (
                    ui.input("Label", placeholder="Blood Test Room 1")
                    .props("outlined dense")
                    .classes("w-full")
                )
                ui.button("Add counter", icon="add", on_click=add_counter).props(
                    "unelevated no-caps"
                ).classes("w-full").style(
                    "margin-top:8px;background: var(--mq-primary)"
                )

            with ui.card().classes("mq-card"):
                ui.label("Set total counters").classes("mq-section-title")
                ui.label(
                    "Creates every missing counter from #1 up to the number you enter. "
                    "Existing counters are left untouched."
                ).classes("mq-muted")
                ensure_total = (
                    ui.number(
                        "Total counters", value=max_number, min=0, precision=0
                    )
                    .props("outlined dense")
                    .classes("w-full")
                    .style("margin-top:8px")
                )
                ui.button(
                    "Apply total", icon="grid_view", on_click=apply_total
                ).props("outline no-caps").classes("w-full").style("margin-top:8px")

    notifications = hub.subscribe()

    async def listen() -> None:
        try:
            while True:
                await notifications.get()
                overview.refresh()
        finally:
            hub.unsubscribe(notifications)

    task = background_tasks.create(listen(), name="mediqueue-admin")
    ui.context.client.on_disconnect(
        lambda: (task.cancel(), hub.unsubscribe(notifications))
    )
