"""Main worker process that consumes jobs from Redis queue."""

import json
import signal
import sys
from typing import Any, NoReturn

import structlog
from redis import Redis

from runner.config import settings
from runner.tasks.export_deck import export_deck
from runner.tasks.run_pipeline import run_pipeline

logger = structlog.get_logger()

QUEUE_NAME = "slide2anki:jobs"


def create_redis_connection() -> Redis:
    """Create Redis connection from settings."""
    return Redis.from_url(settings.redis_url)


def dequeue_task(redis_conn: Redis, timeout: int = 5) -> dict[str, Any] | None:
    """Block until a task payload is available or timeout occurs."""
    result = redis_conn.blpop(QUEUE_NAME, timeout=timeout)
    if not result:
        return None
    _, data = result
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        logger.warning("invalid_task_payload", payload=data)
        return None
    if not isinstance(payload, dict):
        logger.warning("unexpected_task_payload", payload=payload)
        return None
    return payload


def handle_task(payload: dict[str, Any]) -> None:
    """Dispatch a task payload to the correct handler."""
    kind = payload.get("kind")
    if kind == "pipeline":
        job_id = payload.get("job_id")
        if not isinstance(job_id, str):
            logger.warning("missing_job_id", payload=payload)
            return
        run_pipeline(job_id)
        return

    if kind == "export":
        export_id = payload.get("export_id")
        if not isinstance(export_id, str):
            logger.warning("missing_export_id", payload=payload)
            return
        export_deck(export_id)
        return

    logger.warning("unknown_task_kind", payload=payload)


def handle_shutdown(signum: int, frame) -> NoReturn:
    """Handle shutdown signals gracefully."""
    logger.info("received_shutdown_signal", signal=signum)
    sys.exit(0)


def main() -> None:
    """Main entry point for the worker."""
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    logger.info(
        "starting_worker",
        worker_id=settings.worker_id,
        redis_url=settings.redis_url,
        log_level=settings.log_level,
        queue=QUEUE_NAME,
    )

    redis_conn = create_redis_connection()
    logger.info("worker_ready")

    try:
        while True:
            payload = dequeue_task(redis_conn)
            if payload:
                handle_task(payload)
    except Exception as exc:
        logger.exception("worker_error", error=str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
