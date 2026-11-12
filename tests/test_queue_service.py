"""Unit tests for the queue domain service."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.database import init_database
from app.models import DisplayLayout, TicketStatus
from app.services.queue_service import QueueService


@pytest.fixture()
def service(tmp_path: Path) -> QueueService:
    url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    return QueueService(init_database(url))


@pytest.fixture()
def counter_id(service: QueueService) -> int:
    counter = service.create_counter(number=1, label="Registration")
    assert counter.id is not None
    return counter.id


def test_create_and_list_counters(service: QueueService) -> None:
    service.create_counter(number=2, label="Pharmacy")
    service.create_counter(number=1, label="Registration")

    numbers = [counter.number for counter in service.list_counters()]
    assert numbers == [1, 2]


def test_duplicate_counter_number_rejected(service: QueueService) -> None:
    service.create_counter(number=1, label="Registration")
    with pytest.raises(ValueError, match="already exists"):
        service.create_counter(number=1, label="Duplicate")


def test_issue_ticket_increments_numbers(service: QueueService, counter_id: int) -> None:
    first = service.issue_ticket(counter_id)
    second = service.issue_ticket(counter_id)

    assert (first.number, second.number) == (1, 2)
    assert first.status == TicketStatus.waiting
    snapshot = service.queue_snapshot(counter_id)
    assert snapshot is not None
    assert [ticket.number for ticket in snapshot.waiting] == [1, 2]


def test_call_next_serves_and_completes(service: QueueService, counter_id: int) -> None:
    for _ in range(3):
        service.issue_ticket(counter_id)

    first = service.call_next(counter_id)
    assert first is not None and first.number == 1

    second = service.call_next(counter_id)
    assert second is not None and second.number == 2

    snapshot = service.queue_snapshot(counter_id)
    assert snapshot is not None
    assert snapshot.serving is not None and snapshot.serving.number == 2
    assert [ticket.number for ticket in snapshot.waiting] == [3]
    assert snapshot.done_count == 1


def test_call_next_on_empty_queue_returns_none(
    service: QueueService, counter_id: int
) -> None:
    assert service.call_next(counter_id) is None


def test_call_specific_ticket(service: QueueService, counter_id: int) -> None:
    for _ in range(3):
        service.issue_ticket(counter_id)
    snapshot = service.queue_snapshot(counter_id)
    assert snapshot is not None

    chosen = snapshot.waiting[2]
    assert chosen.id is not None
    served = service.call_ticket(counter_id, chosen.id)
    assert served.number == 3
    assert served.status == TicketStatus.serving


def test_complete_skip_and_recall(service: QueueService, counter_id: int) -> None:
    service.issue_ticket(counter_id)
    service.call_next(counter_id)

    assert service.recall_current(counter_id) is True
    assert service.complete_current(counter_id) is True
    assert service.complete_current(counter_id) is False

    service.issue_ticket(counter_id)
    service.call_next(counter_id)
    assert service.skip_current(counter_id) is True

    snapshot = service.queue_snapshot(counter_id)
    assert snapshot is not None
    assert snapshot.serving is None
    assert snapshot.done_count == 1


def test_reorder_waiting_tickets(service: QueueService, counter_id: int) -> None:
    for _ in range(3):
        service.issue_ticket(counter_id)
    snapshot = service.queue_snapshot(counter_id)
    assert snapshot is not None
    third = snapshot.waiting[2]
    assert third.id is not None

    assert service.reorder_ticket(counter_id, third.id, "up") is True
    snapshot = service.queue_snapshot(counter_id)
    assert snapshot is not None
    assert [ticket.number for ticket in snapshot.waiting] == [1, 3, 2]

    first = snapshot.waiting[0]
    assert first.id is not None
    assert service.reorder_ticket(counter_id, first.id, "up") is False


def test_clear_queue_resets_numbering(service: QueueService, counter_id: int) -> None:
    service.issue_ticket(counter_id)
    service.issue_ticket(counter_id)
    assert service.clear_queue(counter_id) == 2

    snapshot = service.queue_snapshot(counter_id)
    assert snapshot is not None
    assert snapshot.waiting == []
    assert snapshot.serving is None

    assert service.issue_ticket(counter_id).number == 1


def test_ensure_total_counters(service: QueueService) -> None:
    created = service.ensure_total_counters(4)
    assert [counter.number for counter in created] == [1, 2, 3, 4]

    again = service.ensure_total_counters(3)
    assert again == []
    assert [counter.number for counter in service.list_counters()] == [1, 2, 3, 4]


def test_delete_counter_removes_tickets(service: QueueService, counter_id: int) -> None:
    service.issue_ticket(counter_id)
    service.delete_counter(counter_id)

    assert service.get_counter(counter_id) is None
    assert service.queue_snapshot(counter_id) is None


def test_layout_roundtrip(service: QueueService, counter_id: int) -> None:
    layout = DisplayLayout(
        show_next=False,
        show_waiting=True,
        show_eta=False,
        show_message=True,
        message="Welcome",
        accent_color="#2563eb",
        avg_service_minutes=7,
    )
    service.set_counter_layout(counter_id, layout)

    counter = service.get_counter(counter_id)
    assert counter is not None
    loaded = counter.display_layout()
    assert loaded.show_next is False
    assert loaded.accent_color == "#2563eb"
    assert loaded.avg_service_minutes == 7


def test_counter_summaries(service: QueueService, counter_id: int) -> None:
    service.issue_ticket(counter_id)
    service.issue_ticket(counter_id)
    service.call_next(counter_id)

    summaries = service.counter_summaries()
    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.serving_number == "1"
    assert summary.waiting_count == 1
    assert summary.done_count == 0


def test_issue_ticket_with_custom_alphanumeric_number(
    service: QueueService, counter_id: int
) -> None:
    first = service.issue_ticket(counter_id, custom_number="A12")
    assert first.display_number == "A12"
    assert first.number == 1  # the numeric sequence is still tracked internally

    second = service.issue_ticket(counter_id)
    assert second.display_number == "2"

    snapshot = service.queue_snapshot(counter_id)
    assert snapshot is not None
    assert snapshot.next_numbers == ["A12", "2"]


def test_update_ticket_number_supports_letters(
    service: QueueService, counter_id: int
) -> None:
    ticket = service.issue_ticket(counter_id)
    assert ticket.id is not None

    updated = service.update_ticket_number(ticket.id, "B-07")
    assert updated.display_number == "B-07"

    snapshot = service.queue_snapshot(counter_id)
    assert snapshot is not None
    assert snapshot.waiting[0].display_number == "B-07"


def test_numeric_renumber_affects_next_issued_number(
    service: QueueService, counter_id: int
) -> None:
    first = service.issue_ticket(counter_id)
    second = service.issue_ticket(counter_id)
    assert second.id is not None

    service.update_ticket_number(second.id, "10")
    assert service.issue_ticket(counter_id).display_number == "11"
    assert first.display_number == "1"


def test_duplicate_or_invalid_ticket_numbers_rejected(
    service: QueueService, counter_id: int
) -> None:
    first = service.issue_ticket(counter_id)
    second = service.issue_ticket(counter_id)
    assert first.id is not None
    assert second.id is not None

    with pytest.raises(ValueError, match="already used"):
        service.update_ticket_number(second.id, first.display_number)
    with pytest.raises(ValueError, match="empty"):
        service.update_ticket_number(second.id, "   ")
    with pytest.raises(ValueError, match="letters, digits"):
        service.update_ticket_number(second.id, "A#1")
    with pytest.raises(ValueError, match="20 characters"):
        service.update_ticket_number(second.id, "A" * 21)

    # Uniqueness is case-insensitive for alphanumeric numbers.
    service.update_ticket_number(first.id, "A1")
    with pytest.raises(ValueError, match="already used"):
        service.update_ticket_number(second.id, "a1")
    with pytest.raises(ValueError, match="already used"):
        service.issue_ticket(counter_id, custom_number="A1")
