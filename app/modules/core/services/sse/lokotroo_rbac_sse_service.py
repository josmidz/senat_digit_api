import asyncio
import json
import os
import time
from contextlib import suppress
from typing import Any, AsyncGenerator, Dict

import redis.asyncio as aioredis


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


class SenatDigitAppsSseService:
    """Redis Pub/Sub-backed SSE service for the apps tree load."""

    _CHANNEL_PREFIX = "senat_digit_apps_sse:"

    @classmethod
    def _channel(cls, sse_key: str) -> str:
        return f"{cls._CHANNEL_PREFIX}{sse_key}"

    @classmethod
    async def publish(cls, sse_key: str, payload: Dict[str, Any]) -> None:
        if not sse_key:
            return
        async with aioredis.from_url(_redis_url()) as client:
            await client.publish(
                cls._channel(sse_key),
                json.dumps(payload, default=str),
            )

    @classmethod
    async def stream(
        cls,
        sse_key: str,
        request,
        heartbeat_seconds: int = 10,
        max_lifetime_seconds: int = 300,
    ) -> AsyncGenerator[str, None]:
        if not sse_key:
            yield "event: error\ndata: {\"event\":\"error\",\"message\":\"Missing sse_key\"}\n\n"
            return

        channel = cls._channel(sse_key)
        created_at = time.time()
        local_queue: asyncio.Queue = asyncio.Queue()

        async def _redis_listener() -> None:
            async with aioredis.from_url(_redis_url()) as client:
                pubsub = client.pubsub()
                await pubsub.subscribe(channel)
                try:
                    async for message in pubsub.listen():
                        if message and message.get("type") == "message":
                            await local_queue.put(message["data"])
                finally:
                    with suppress(Exception):
                        await pubsub.unsubscribe(channel)

        listener_task = asyncio.create_task(_redis_listener())

        try:
            while True:
                if await request.is_disconnected():
                    break

                if time.time() - created_at > max_lifetime_seconds:
                    yield "event: timeout\ndata: {\"event\":\"timeout\",\"message\":\"SSE channel expired\"}\n\n"
                    break

                try:
                    raw = await asyncio.wait_for(
                        local_queue.get(),
                        timeout=heartbeat_seconds,
                    )
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                    continue

                try:
                    payload = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    continue

                event_name = payload.get("event", "progress")
                data = json.dumps(payload, default=str)
                yield f"event: {event_name}\ndata: {data}\n\n"

                if event_name in {"complete", "error"}:
                    break
        finally:
            listener_task.cancel()
            with suppress(asyncio.CancelledError):
                await listener_task


LokotrooRbacSseService = SenatDigitAppsSseService
