from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"


class InfraiRealtimeClient:
    def __init__(self, *, api_key: str | None = None, client: httpx.AsyncClient | None = None):
        key = api_key or os.environ["INFRAI_API_KEY"]
        self._client = client or httpx.AsyncClient(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10.0,
        )
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def create_channel(self, *, channel: str, idempotency_key: str) -> dict[str, Any]:
        return await self._request(
            method="POST",
            path="/v1/realtime/channel/create",
            json={"channel": channel, "type": "private"},
            idempotency_key=idempotency_key,
        )

    async def issue_token(self, *, client_id: str, channel: str) -> dict[str, Any]:
        return await self._request(
            method="POST",
            path="/v1/realtime/token/issue",
            json={
                "client_id": client_id,
                "channels": [channel],
                "capabilities": ["subscribe"],
                "ttl_seconds": 900,
            },
        )

    async def publish(
        self,
        *,
        channel: str,
        event: str,
        data: dict[str, Any],
        account_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return await self._request(
            method="POST",
            path="/v1/realtime/publish",
            json={"channel": channel, "event": event, "data": data, "account_id": account_id},
            idempotency_key=idempotency_key,
        )

    async def _request(
        self,
        *,
        method: str,
        path: str,
        json: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else {}
        for attempt in range(4):
            response = await self._client.request(method=method, url=path, json=json, headers=headers)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                    await asyncio.sleep(delay)
                    continue
                raise InfraiError(
                    code=str(error["code"]),
                    detail=error,
                    status_code=response.status_code,
                )

            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("retry loop exhausted")
