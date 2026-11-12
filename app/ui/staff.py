"""Staff console: call, complete, reorder and reset queues."""

from __future__ import annotations

from typing import Literal

from nicegui import app, background_tasks, ui

from ..bootstrap import get_service
from ..services.realtime import hub
from .session import require
from .theme import page_frame

STAFF_COUNTER_KEY = "staff_counter_id"
Direction = Literal["up", "down"]


@ui.page("/staff", title="MediQueue — Staff console")
async def staff_page() -> None:
    if not require("staff"):
        return
    page_frame(active="staff")
    service = get_service()
    counters = service.list_counters(active_only=True)

    if not counters:
        with ui.column().classes("mq-shell"):
            ui.label("Staff console").classes("mq-title")
            with ui.card().classes("mq-card"):
                ui.label("No counters are configured yet.").classes("mq-section-title")
                ui.label("Ask an administrator to add a counter first.").classes("mq-muted")
                ui.button(
                    "Open admin",
                    icon="settings",
                    on_click=lambda: ui.navigate.to("/admin"),
                ).props("outline no-caps").classes("w-full").style("margin-top:8px")
        return

    saved = app.storage.user.get(STAFF_COUNTER_KEY)
    valid_ids = {counter.id for counter in counters}
    default_id = saved if isinstance(saved, int) and saved in valid_ids else counters[0].id
    state: dict[str, int | None] = {"counter_id": default_id}
    number_mode: dict[str, str] = {"mode": "edit"}
    number_target: dict[str, int | None] = {"ticket_id": None}
    options = {
        counter.id: f"#{counter.number} · {counter.label or 'Counter'}"
        for counter in counters
        if counter.id is not None
    }

    def current_counter_id() -> int:
        counter_id = state["counter_id"]
        assert counter_id is not None, "A counter must be selected"
        return counter_id

    def publish_refresh() -> None:
        # The page's hub listener refreshes every connected console (including this one).
        hub.publish()

    def change_counter(value: int | None) -> None:
        if value is None:
            return
        state["counter_id"] = int(value)
        app.storage.user[STAFF_COUNTER_KEY] = int(value)
        panels.refresh()

    @ui.refreshable
    def panels() -> None:
        snapshot = service.queue_snapshot(current_counter_id())
        with ui.element("div").classes("mq-grid-2"):
            with ui.card().classes("mq-card"):
                ui.label("Now serving").classes("mq-muted")
                if snapshot and snapshot.serving:
                    serving = snapshot.serving
                    ui.label(f"#{serving.display_number}").classes("mq-serving-number")
                    if serving.note:
                        ui.label(serving.note).classes("mq-muted")
                    # Timestamps are stored in UTC; show them in the server's local time.
                    called = (
                        serving.called_at.astimezone().strftime("%H:%M")
                        if serving.called_at
                        else "—"
                    )
                    ui.label(f"Called at {called}").classes("mq-muted")
                    with ui.row().classes("mq-actions").style("margin-top:10px"):
                        ui.button(
                            "Complete", icon="check", on_click=do_complete
                        ).props("unelevated no-caps color=positive")
                        ui.button("Skip", icon="skip_next", on_click=do_skip).props(
                            "outline no-caps"
                        )
                        ui.button("Recall", icon="campaign", on_click=do_recall).props(
                            "outline no-caps"
                        )
                        ui.button(
                            icon="edit",
                            on_click=lambda _=None, tid=serving.id: (
                                open_edit_number(tid) if tid is not None else None
                            ),
                        ).props("flat round dense").tooltip("Change ticket number")
                else:
                    ui.label("—").classes("mq-serving-number")
                    ui.label("No ticket is being served.").classes("mq-muted")
                ui.separator()
                ui.label(f"Completed: {snapshot.done_count if snapshot else 0}").classes(
                    "mq-muted"
                )

            with ui.card().classes("mq-card"):
                waiting = snapshot.waiting if snapshot else []
                with ui.row().classes("w-full items-center"):
                    ui.label("Waiting queue").classes("mq-section-title")
                    ui.space()
                    ui.label(f"{len(waiting)} waiting").classes("mq-muted")
                if not waiting:
                    ui.label("The waiting queue is empty.").classes("mq-muted").style(
                        "margin-top:12px"
                    )
                for index, ticket in enumerate(waiting, start=1):
                    with ui.row().classes("mq-queue-row w-full"):
                        ui.label(str(index)).classes("mq-pos")
                        ui.label(f"#{ticket.display_number}").classes("mq-ticket")
                        if ticket.note:
                            ui.label(ticket.note).classes("mq-muted")
                        ui.space()
                        ui.button(
                            icon="edit",
                            on_click=lambda _=None, tid=ticket.id: (
                                open_edit_number(tid) if tid is not None else None
                            ),
                        ).props("flat round dense").tooltip("Change ticket number")
                        ui.button(
                            icon="arrow_upward",
                            on_click=lambda _=None, tid=ticket.id: do_move(tid, "up"),
                        ).props("flat round dense").set_enabled(index > 1)
                        ui.button(
                            icon="arrow_downward",
                            on_click=lambda _=None, tid=ticket.id: do_move(tid, "down"),
                        ).props("flat round dense").set_enabled(index < len(waiting))
                        ui.button(
                            "Call",
                            on_click=lambda _=None, tid=ticket.id: do_call_ticket(tid),
                        ).props("dense unelevated no-caps")

    def do_call_next() -> None:
        ticket = service.call_next(current_counter_id())
        if ticket is None:
            ui.notify("No one is waiting.", type="info")
        else:
            ui.notify(f"Called ticket #{ticket.display_number}", type="positive")
        publish_refresh()

    def do_issue() -> None:
        ticket = service.issue_ticket(current_counter_id())
        ui.notify(f"Issued ticket #{ticket.display_number}", type="positive")
        publish_refresh()

    def do_complete() -> None:
        completed = service.complete_current(current_counter_id())
        ui.notify(
            "Ticket completed." if completed else "No ticket is being served.",
            type="positive" if completed else "info",
        )
        publish_refresh()

    def do_skip() -> None:
        skipped = service.skip_current(current_counter_id())
        ui.notify(
            "Ticket skipped." if skipped else "No ticket is being served.",
            type="warning" if skipped else "info",
        )
        publish_refresh()

    def do_recall() -> None:
        recalled = service.recall_current(current_counter_id())
        ui.notify(
            "Ticket re-announced." if recalled else "No ticket is being served.",
            type="info",
        )
        publish_refresh()

    def do_call_ticket(ticket_id: int | None) -> None:
        if ticket_id is None:
            return
        try:
            ticket = service.call_ticket(current_counter_id(), ticket_id)
        except ValueError as exc:
            ui.notify(str(exc), type="negative")
            return
        ui.notify(f"Now serving #{ticket.display_number}", type="positive")
        publish_refresh()

    def do_move(ticket_id: int | None, direction: Direction) -> None:
        if ticket_id is None:
            return
        if service.reorder_ticket(current_counter_id(), ticket_id, direction):
            publish_refresh()

    def open_edit_number(ticket_id: int | None) -> None:
        """Open the number dialog for an existing ticket."""
        if ticket_id is None:
            return
        ticket = service.get_ticket(ticket_id)
        if ticket is None:
            ui.notify("Ticket no longer exists.", type="negative")
            return
        number_mode["mode"] = "edit"
        number_target["ticket_id"] = ticket_id
        number_title.set_text("Change ticket number")
        number_input.value = ticket.display_number
        number_error.set_text("")
        number_dialog.open()

    def open_custom_issue() -> None:
        """Open the number dialog to issue a ticket with a chosen number."""
        number_mode["mode"] = "issue"
        number_target["ticket_id"] = None
        number_title.set_text("Issue ticket with a custom number")
        number_input.value = ""
        number_error.set_text("")
        number_dialog.open()

    def save_number() -> None:
        """Validate and apply a staff-entered ticket number (letters allowed)."""
        raw = str(number_input.value or "").strip()
        try:
            if number_mode["mode"] == "issue":
                ticket = service.issue_ticket(
                    current_counter_id(),
                    custom_number=raw or None,
                )
                ui.notify(f"Issued ticket #{ticket.display_number}", type="positive")
            else:
                ticket_id = number_target["ticket_id"]
                if ticket_id is None:
                    return
                ticket = service.update_ticket_number(ticket_id, raw)
                ui.notify(
                    f"Ticket number changed to #{ticket.display_number}.",
                    type="positive",
                )
        except ValueError as exc:
            number_error.set_text(str(exc))
            return
        number_dialog.close()
        publish_refresh()

    def confirm_reset() -> None:
        removed = service.clear_queue(current_counter_id())
        reset_dialog.close()
        ui.notify(f"Queue cleared ({removed} tickets removed).", type="warning")
        publish_refresh()

    with ui.dialog() as reset_dialog, ui.card().classes("mq-dialog"):
        ui.label("Reset the queue?").classes("mq-section-title")
        ui.label(
            "All tickets for this counter will be deleted and numbering restarts at #1. "
            "This cannot be undone."
        ).classes("mq-muted")
        with ui.row().classes("w-full justify-end").style("margin-top:12px"):
            ui.button("Cancel", on_click=reset_dialog.close).props("flat no-caps")
            ui.button("Reset queue", on_click=confirm_reset).props(
                "unelevated no-caps color=negative"
            )

    with ui.dialog() as number_dialog, ui.card().classes("mq-dialog"):
        number_title = ui.label("Ticket number").classes("mq-section-title")
        ui.label(
            "Letters and digits are allowed (A12, B-03, VIP 1). The number must be "
            "unique within this counter and at most 20 characters."
        ).classes("mq-muted")
        number_input = ui.input("Number").props("outlined dense").classes("w-full")
        number_error = ui.label("").classes("mq-error")
        with ui.row().classes("w-full justify-end"):
            ui.button("Cancel", on_click=number_dialog.close).props("flat no-caps")
            ui.button("Save", on_click=save_number).props("unelevated no-caps").style(
                "background: var(--mq-primary)"
            )

    with ui.column().classes("mq-shell mq-shell-wide"):
        with ui.row().classes("w-full items-end"):
            with ui.column().style("gap:2px"):
                ui.label("Staff console").classes("mq-title")
                ui.label("Call, complete and reorder tickets in real time.").classes(
                    "mq-subtitle"
                )
            ui.space()
            ui.select(
                options=options,
                value=state["counter_id"],
                label="Counter",
                on_change=lambda event: change_counter(event.value),
            ).props("outlined dense").style("min-width:220px")

        with ui.row().classes("mq-actions"):
            ui.button("Issue ticket", icon="add", on_click=do_issue).props(
                "outline no-caps"
            )
            ui.button(
                "Custom ticket", icon="edit_note", on_click=open_custom_issue
            ).props("outline no-caps")
            ui.button(
                "Call next", icon="record_voice_over", on_click=do_call_next
            ).props("unelevated no-caps").style("background: var(--mq-primary)")
            ui.button(
                "Reset queue", icon="delete_sweep", on_click=reset_dialog.open
            ).props("flat no-caps color=negative")

        panels()

    notifications = hub.subscribe()

    async def listen() -> None:
        try:
            while True:
                await notifications.get()
                panels.refresh()
        finally:
            hub.unsubscribe(notifications)

    task = background_tasks.create(listen(), name="mediqueue-staff")
    ui.context.client.on_disconnect(
        lambda: (task.cancel(), hub.unsubscribe(notifications))
    )
