"""Queue domain logic.

Every method opens a short-lived SQLModel session and commits its own
transaction, which keeps request handlers free of database bookkeeping.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from sqlalchemy import func
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from ..models import Counter, DisplayLayout, Ticket, TicketStatus, utcnow

ReorderDirection = Literal["up", "down"]


@dataclass(frozen=True, slots=True)
class QueueSnapshot:
    """Everything a display needs to render a counter at one point in time."""

    counter: Counter
    layout: DisplayLayout
    serving: Ticket | None
    waiting: list[Ticket]
    done_count: int

    @property
    def waiting_count(self) -> int:
        return len(self.waiting)

    @property
    def eta_minutes(self) -> int:
        return self.waiting_count * self.layout.avg_service_minutes

    @property
    def next_numbers(self) -> list[str]:
        return [ticket.display_number for ticket in self.waiting[:5]]


@dataclass(frozen=True, slots=True)
class CounterSummary:
    """Compact admin overview of a single counter."""

    counter: Counter
    serving_number: str | None
    waiting_count: int
    done_count: int


class QueueService:
    """Stateless service holding only the database engine."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    # -- session helpers -------------------------------------------------
    def _session(self) -> Session:
        return Session(self._engine, expire_on_commit=False)

    @staticmethod
    def _get_counter_or_raise(session: Session, counter_id: int) -> Counter:
        counter = session.get(Counter, counter_id)
        if counter is None:
            raise ValueError(f"Counter {counter_id} does not exist")
        return counter

    @staticmethod
    def _normalize_ticket_number(value: str) -> str:
        """Validate a staff-entered ticket number: alphanumerics plus ``-_`` and spaces."""
        normalized = " ".join((value or "").split())
        if not normalized:
            raise ValueError("Ticket number cannot be empty")
        if len(normalized) > 20:
            raise ValueError("Ticket number must be 20 characters or fewer")
        if not any(character.isalnum() for character in normalized):
            raise ValueError("Ticket number must contain at least one letter or digit")
        if any(
            not (character.isalnum() or character in "-_ ")
            for character in normalized
        ):
            raise ValueError("Use letters, digits, spaces, '-' or '_' only")
        return normalized

    def _assert_number_available(
        self,
        session: Session,
        counter_id: int,
        value: str,
        *,
        exclude_ticket_id: int | None = None,
    ) -> None:
        """Reject duplicate display numbers within one counter (case-insensitive)."""
        statement = select(Ticket).where(Ticket.counter_id == counter_id)
        for other in session.exec(statement).all():
            if exclude_ticket_id is not None and other.id == exclude_ticket_id:
                continue
            if other.display_number.casefold() == value.casefold():
                raise ValueError(f"Ticket number {value} is already used in this queue")

    @staticmethod
    def _apply_custom_number(ticket: Ticket, normalized: str) -> None:
        """Numeric input updates the sequence; anything else becomes a display code."""
        if normalized.isascii() and normalized.isdigit():
            ticket.number = int(normalized)
            ticket.code = ""
        else:
            ticket.code = normalized

    @staticmethod
    def _current_serving(session: Session, counter_id: int) -> Ticket | None:
        statement = (
            select(Ticket)
            .where(
                Ticket.counter_id == counter_id,
                Ticket.status == TicketStatus.serving,
            )
            .order_by(Ticket.called_at.desc())  # type: ignore[union-attr]
        )
        return session.exec(statement).first()

    @staticmethod
    def _waiting_tickets(session: Session, counter_id: int) -> list[Ticket]:
        statement = (
            select(Ticket)
            .where(
                Ticket.counter_id == counter_id,
                Ticket.status == TicketStatus.waiting,
            )
            .order_by(Ticket.position, Ticket.number)
        )
        return list(session.exec(statement).all())

    def _finish_serving(self, session: Session, counter_id: int) -> Ticket | None:
        """Mark the ticket currently being served as done (if any)."""
        serving = self._current_serving(session, counter_id)
        if serving is not None:
            serving.status = TicketStatus.done
            serving.finished_at = utcnow()
            session.add(serving)
        return serving

    # -- counters --------------------------------------------------------
    def list_counters(self, *, active_only: bool = False) -> list[Counter]:
        with self._session() as session:
            statement = select(Counter).order_by(Counter.number)
            if active_only:
                statement = statement.where(Counter.active.is_(True))
            return list(session.exec(statement).all())

    def get_counter(self, counter_id: int) -> Counter | None:
        with self._session() as session:
            return session.get(Counter, counter_id)

    def get_ticket(self, ticket_id: int) -> Ticket | None:
        with self._session() as session:
            return session.get(Ticket, ticket_id)

    def create_counter(self, *, number: int, label: str = "") -> Counter:
        with self._session() as session:
            clash = session.exec(select(Counter).where(Counter.number == number)).first()
            if clash is not None:
                raise ValueError(f"Counter number {number} already exists")
            counter = Counter(number=number, label=label.strip())
            session.add(counter)
            session.commit()
            session.refresh(counter)
            return counter

    def update_counter(
        self,
        counter_id: int,
        *,
        number: int | None = None,
        label: str | None = None,
        active: bool | None = None,
        layout: DisplayLayout | None = None,
    ) -> Counter:
        with self._session() as session:
            counter = self._get_counter_or_raise(session, counter_id)
            if number is not None and number != counter.number:
                clash = session.exec(select(Counter).where(Counter.number == number)).first()
                if clash is not None:
                    raise ValueError(f"Counter number {number} already exists")
                counter.number = number
            if label is not None:
                counter.label = label.strip()
            if active is not None:
                counter.active = active
            if layout is not None:
                counter.set_display_layout(layout)
            session.add(counter)
            session.commit()
            session.refresh(counter)
            return counter

    def set_counter_layout(self, counter_id: int, layout: DisplayLayout) -> Counter:
        return self.update_counter(counter_id, layout=layout)

    def delete_counter(self, counter_id: int) -> None:
        with self._session() as session:
            counter = self._get_counter_or_raise(session, counter_id)
            tickets = session.exec(select(Ticket).where(Ticket.counter_id == counter_id)).all()
            for ticket in tickets:
                session.delete(ticket)
            session.delete(counter)
            session.commit()

    def ensure_total_counters(self, total: int) -> list[Counter]:
        """Create missing counters numbered 1..total without touching existing ones."""
        if total < 0:
            raise ValueError("Total counters cannot be negative")
        with self._session() as session:
            existing = {counter.number for counter in session.exec(select(Counter)).all()}
            created: list[Counter] = []
            for number in range(1, total + 1):
                if number in existing:
                    continue
                counter = Counter(number=number, label=f"Counter {number}")
                session.add(counter)
                created.append(counter)
            session.commit()
            for counter in created:
                session.refresh(counter)
            return created

    # -- tickets ---------------------------------------------------------
    def issue_ticket(
        self,
        counter_id: int,
        *,
        note: str = "",
        custom_number: str | None = None,
    ) -> Ticket:
        """Issue a ticket, optionally with an alphanumeric number chosen by staff."""
        with self._session() as session:
            self._get_counter_or_raise(session, counter_id)
            last_number = session.scalar(
                select(func.max(Ticket.number)).where(Ticket.counter_id == counter_id)
            )
            last_position = session.scalar(
                select(func.max(Ticket.position)).where(Ticket.counter_id == counter_id)
            )
            ticket = Ticket(
                counter_id=counter_id,
                number=int(last_number or 0) + 1,
                position=int(last_position or 0) + 1,
                note=note.strip(),
            )
            if custom_number is not None and custom_number.strip():
                normalized = self._normalize_ticket_number(custom_number)
                self._assert_number_available(session, counter_id, normalized)
                self._apply_custom_number(ticket, normalized)
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            return ticket

    def call_next(self, counter_id: int) -> Ticket | None:
        """Complete the current ticket and promote the first waiting one."""
        with self._session() as session:
            self._get_counter_or_raise(session, counter_id)
            self._finish_serving(session, counter_id)
            waiting = self._waiting_tickets(session, counter_id)
            if not waiting:
                session.commit()
                return None
            ticket = waiting[0]
            ticket.status = TicketStatus.serving
            ticket.called_at = utcnow()
            ticket.finished_at = None
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            return ticket

    def call_ticket(self, counter_id: int, ticket_id: int) -> Ticket:
        """Serve a specific ticket, completing whatever was being served."""
        with self._session() as session:
            ticket = session.get(Ticket, ticket_id)
            if ticket is None or ticket.counter_id != counter_id:
                raise ValueError("Ticket does not belong to this counter")
            if ticket.status == TicketStatus.done:
                raise ValueError("This ticket is already completed")
            if ticket.status != TicketStatus.serving:
                self._finish_serving(session, counter_id)
                ticket.status = TicketStatus.serving
                ticket.finished_at = None
            ticket.called_at = utcnow()
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            return ticket

    def complete_current(self, counter_id: int) -> bool:
        with self._session() as session:
            finished = self._finish_serving(session, counter_id)
            session.commit()
            return finished is not None

    def skip_current(self, counter_id: int) -> bool:
        with self._session() as session:
            serving = self._current_serving(session, counter_id)
            if serving is None:
                return False
            serving.status = TicketStatus.skipped
            serving.finished_at = utcnow()
            session.add(serving)
            session.commit()
            return True

    def recall_current(self, counter_id: int) -> bool:
        """Re-announce the ticket currently being served."""
        with self._session() as session:
            serving = self._current_serving(session, counter_id)
            if serving is None:
                return False
            serving.called_at = utcnow()
            session.add(serving)
            session.commit()
            return True

    def update_ticket_number(self, ticket_id: int, value: str) -> Ticket:
        """Change a ticket's displayed number, allowing letters (e.g. ``A12``)."""
        with self._session() as session:
            ticket = session.get(Ticket, ticket_id)
            if ticket is None:
                raise ValueError("Ticket does not exist")
            normalized = self._normalize_ticket_number(value)
            self._assert_number_available(
                session,
                ticket.counter_id,
                normalized,
                exclude_ticket_id=ticket.id,
            )
            self._apply_custom_number(ticket, normalized)
            session.add(ticket)
            session.commit()
            session.refresh(ticket)
            return ticket

    def reorder_ticket(
        self,
        counter_id: int,
        ticket_id: int,
        direction: ReorderDirection,
    ) -> bool:
        """Move a waiting ticket one step up or down in the queue."""
        with self._session() as session:
            waiting = self._waiting_tickets(session, counter_id)
            index = next((i for i, ticket in enumerate(waiting) if ticket.id == ticket_id), None)
            if index is None:
                return False
            target = index - 1 if direction == "up" else index + 1
            if target < 0 or target >= len(waiting):
                return False
            waiting[index], waiting[target] = waiting[target], waiting[index]
            for position, ticket in enumerate(waiting, start=1):
                ticket.position = position
                session.add(ticket)
            session.commit()
            return True

    def clear_queue(self, counter_id: int) -> int:
        """Delete every ticket of a counter; numbering restarts at 1."""
        with self._session() as session:
            self._get_counter_or_raise(session, counter_id)
            tickets = list(
                session.exec(select(Ticket).where(Ticket.counter_id == counter_id)).all()
            )
            for ticket in tickets:
                session.delete(ticket)
            session.commit()
            return len(tickets)

    # -- read models -----------------------------------------------------
    def queue_snapshot(self, counter_id: int) -> QueueSnapshot | None:
        with self._session() as session:
            counter = session.get(Counter, counter_id)
            if counter is None:
                return None
            serving = self._current_serving(session, counter_id)
            waiting = self._waiting_tickets(session, counter_id)
            done_count = int(
                session.scalar(
                    select(func.count())
                    .select_from(Ticket)
                    .where(
                        Ticket.counter_id == counter_id,
                        Ticket.status == TicketStatus.done,
                    )
                )
                or 0
            )
            return QueueSnapshot(
                counter=counter,
                layout=counter.display_layout(),
                serving=serving,
                waiting=waiting,
                done_count=done_count,
            )

    def counter_summaries(self) -> list[CounterSummary]:
        with self._session() as session:
            counters = list(session.exec(select(Counter).order_by(Counter.number)).all())
            summaries: list[CounterSummary] = []
            for counter in counters:
                assert counter.id is not None
                serving = self._current_serving(session, counter.id)
                waiting_count = int(
                    session.scalar(
                        select(func.count())
                        .select_from(Ticket)
                        .where(
                            Ticket.counter_id == counter.id,
                            Ticket.status == TicketStatus.waiting,
                        )
                    )
                    or 0
                )
                done_count = int(
                    session.scalar(
                        select(func.count())
                        .select_from(Ticket)
                        .where(
                            Ticket.counter_id == counter.id,
                            Ticket.status == TicketStatus.done,
                        )
                    )
                    or 0
                )
                summaries.append(
                    CounterSummary(
                        counter=counter,
                        serving_number=serving.display_number if serving else None,
                        waiting_count=waiting_count,
                        done_count=done_count,
                    )
                )
            return summaries

    # -- seed ------------------------------------------------------------
    def seed_defaults(self) -> None:
        """Populate a small, sensible set of counters on a fresh database."""
        with self._session() as session:
            if session.exec(select(Counter)).first() is not None:
                return
            for number, label in (
                (1, "Registration"),
                (2, "Blood Test"),
                (3, "Pharmacy"),
            ):
                session.add(Counter(number=number, label=label))
            session.commit()
