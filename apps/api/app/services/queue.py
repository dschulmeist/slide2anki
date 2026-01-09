import json
from typing import Optional

import redis.asyncio as redis

from app.settings import settings

_redis: Optional[redis.Redis] = None

QUEUE_NAME = "slide2anki:jobs"


async def get_redis() -> redis.Redis:
    """Get the Redis client instance."""
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url)
    return _redis


async def enqueue_job(job_id: str) -> None:
    """Add a job to the processing queue."""
    client = await get_redis()
    await client.rpush(QUEUE_NAME, json.dumps({"job_id": job_id}))


async def dequeue_job() -> Optional[str]:
    """Get the next job from the queue (blocking)."""
    client = await get_redis()
    result = await client.blpop(QUEUE_NAME, timeout=5)
    if result:
        _, data = result
        payload = json.loads(data)
        return payload.get("job_id")
    return None


async def publish_progress(job_id: str, progress: int, step: str) -> None:
    """Publish job progress update."""
    client = await get_redis()
    await client.publish(
        f"slide2anki:progress:{job_id}",
        json.dumps({"progress": progress, "step": step}),
    )
