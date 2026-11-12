"""SQLModel table definitions and small value objects."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field as PydanticField
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    """Timezone-aware UTC timestamp used for every stored datetime."""
    return datetime.now(timezone.utc)


class TicketStatus(str, Enum):
    """Lifecycle of a single queue ticket."""

    waiting = "waiting"
    serving = "serving"
    done = "done"
    skipped = "skipped"


class DisplayLayout(BaseModel):
    """Per-counter display configuration managed by admins.

    Stored as JSON on the counter row so the schema stays simple.
    """

    show_next: bool = True
    show_waiting: bool = True
    show_eta: bool = True
    show_message: bool = True
    message: str = "Please have your ticket ready."
    accent_color: str = "#0f766e"
    avg_service_minutes: int = PydanticField(default=5, ge=1, le=120)


class Counter(SQLModel, table=True):
    """A service counter / display screen (e.g. "Pharmacy Window 2")."""

    __tablename__ = "counters"

    id: int | None = Field(default=None, primary_key=True)
    number: int = Field(index=True, unique=True, ge=1)
    label: str = Field(default="", max_length=120)
    active: bool = Field(default=True)
    layout_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=utcnow)

    def display_layout(self) -> DisplayLayout:
        """Parse the stored layout JSON, falling back to defaults on bad data."""
        try:
            return DisplayLayout.model_validate_json(self.layout_json)
        except ValueError:
            return DisplayLayout()

    def set_display_layout(self, layout: DisplayLayout) -> None:
        self.layout_json = layout.model_dump_json()


class Ticket(SQLModel, table=True):
    """A numbered queue ticket belonging to exactly one counter."""

    __tablename__ = "tickets"

    id: int | None = Field(default=None, primary_key=True)
    counter_id: int = Field(foreign_key="counters.id", index=True)
    # Numeric sequence used for auto-issue and ordering; may be overridden by staff.
    number: int = Field(index=True, ge=1)
    # Optional alphanumeric display number (e.g. "A12", "B-03"). Empty means "use number".
    code: str = Field(default="", max_length=20, index=True)
    status: TicketStatus = Field(default=TicketStatus.waiting, index=True)
    position: int = Field(default=0, index=True)
    note: str = Field(default="", max_length=200)
    created_at: datetime = Field(default_factory=utcnow)
    called_at: datetime | None = Field(default=None)
    finished_at: datetime | None = Field(default=None)

    @property
    def display_number(self) -> str:
        """Number shown to patients: the custom code when set, otherwise the sequence."""
        return self.code or str(self.number)
