from __future__ import annotations

import hashlib

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from appointment_notifications import AppointmentUpdate, build_operational_notification
from infrai_realtime import InfraiError, InfraiRealtimeClient


class RoomSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(min_length=1, max_length=80)
    client_id: str = Field(min_length=1, max_length=80)


class RoomSession(BaseModel):
    channel: str
    token: dict[str, object]


class PublishedUpdate(BaseModel):
    channel: str
    event: str
    status: str


app = FastAPI(title="Appointment room notifications")


def _client_error(exc: InfraiError) -> HTTPException:
    status = exc.status_code if 400 <= exc.status_code < 500 else 502
    return HTTPException(status_code=status, detail={"code": exc.code, "error": exc.detail})


@app.post("/room-sessions", response_model=RoomSession)
async def create_room_session(request: RoomSessionRequest) -> RoomSession:
    client = InfraiRealtimeClient()
    channel = f"appointments:{request.account_id}"
    key = hashlib.sha256(f"channel:{channel}".encode()).hexdigest()
    try:
        await client.create_channel(channel=channel, idempotency_key=key)
        token = await client.issue_token(client_id=request.client_id, channel=channel)
        return RoomSession(channel=channel, token=token)
    except InfraiError as exc:
        raise _client_error(exc) from exc
    finally:
        await client.close()


@app.post("/appointment-updates", response_model=PublishedUpdate)
async def publish_appointment_update(update: AppointmentUpdate) -> PublishedUpdate:
    notification = build_operational_notification(update)
    key = hashlib.sha256(
        f"{update.appointment_id}:{update.status.value}:{update.starts_at}".encode()
    ).hexdigest()
    client = InfraiRealtimeClient()
    try:
        await client.publish(
            channel=notification.channel,
            event=notification.event,
            data=notification.data,
            account_id=notification.account_id,
            idempotency_key=key,
        )
    except InfraiError as exc:
        raise _client_error(exc) from exc
    finally:
        await client.close()
    return PublishedUpdate(
        channel=notification.channel,
        event=notification.event,
        status=update.status.value,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("appointment_service:app", host="127.0.0.1", port=8000)
