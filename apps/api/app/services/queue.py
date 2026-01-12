"""Queue and progress utilities backed by Redis."""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any, Literal, TypedDict

import redis.asyncio as redis

from app.settings import settings

_redis: redis.Redis | None = None

QUEUE_NAME = "slide2anki:jobs"

TaskKind = Literal["job", "export"]


class TaskPayload(TypedDict):
    """Serialized task payload for the worker queue."""

    kind: TaskKind
    job_id: str | None
    export_id: str | None


async def get_redis() -> redis.Redis:
    """Get the Redis client instance."""
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url)
    return _redis


async def enqueue_job(job_id: str) -> None:
    """Add a job to the processing queue."""
    client = await get_redis()
    payload: TaskPayload = {
        "kind": "job",
        "job_id": job_id,
        "export_id": None,
    }
    await client.rpush(QUEUE_NAME, json.dumps(payload))


async def enqueue_export_job(export_id: str) -> None:
    """Add an export job to the processing queue."""
    client = await get_redis()
    payload: TaskPayload = {
        "kind": "export",
        "job_id": None,
        "export_id": export_id,
    }
    await client.rpush(QUEUE_NAME, json.dumps(payload))


async def dequeue_task() -> TaskPayload | None:
    """Get the next task from the queue (blocking)."""
    client = await get_redis()
    result = await client.blpop(QUEUE_NAME, timeout=5)
    if result:
        _, data = result
        payload = json.loads(data)
        if isinstance(payload, dict):
            return payload  # type: ignore[return-value]
    return None


async def publish_progress(job_id: str, progress: int, step: str) -> None:
    """Publish job progress update."""
    client = await get_redis()
    await client.publish(
        f"slide2anki:progress:{job_id}",
        json.dumps({"progress": progress, "step": step}),
    )


async def subscribe_progress(
    job_id: str,
    poll_interval: float = 0.25,
) -> AsyncGenerator[dict[str, Any], None]:
    """Subscribe to progress events for a job."""
    client = await get_redis()
    pubsub = client.pubsub()
    channel = f"slide2anki:progress:{job_id}"
    await pubsub.subscribe(channel)

    try:
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )
            if message and message.get("type") == "message":
                data = message.get("data")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                if isinstance(data, str):
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue
            await asyncio.sleep(poll_interval)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
