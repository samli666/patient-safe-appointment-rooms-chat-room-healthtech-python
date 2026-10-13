from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AppointmentStatus(str, Enum):
    CONFIRMED = "confirmed"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"


class AppointmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    appointment_id: str = Field(min_length=1, max_length=80)
    account_id: str = Field(min_length=1, max_length=80)
    status: AppointmentStatus
    starts_at: datetime | None = None
    clinical_note: str | None = Field(default=None, max_length=2000)


class RealtimeNotification(BaseModel):
    channel: str
    event: str
    data: dict[str, Any]
    account_id: str


def build_operational_notification(update: AppointmentUpdate) -> RealtimeNotification:
    """Build the small, non-clinical payload allowed on a chat channel."""
    data: dict[str, Any] = {
        "appointment_id": update.appointment_id,
        "status": update.status.value,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    if update.starts_at is not None:
        data["starts_at"] = update.starts_at.isoformat()

    return RealtimeNotification(
        channel=f"appointments:{update.account_id}",
        event="appointment.status_changed",
        data=data,
        account_id=update.account_id,
    )
