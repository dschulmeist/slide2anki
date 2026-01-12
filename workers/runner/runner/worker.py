"""Main worker process that consumes jobs from Redis queue."""

import json
import signal
import sys
from datetime import datetime
from typing import Any, NoReturn

import structlog
from redis import Redis
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from runner.config import settings
from runner.tasks.build_markdown import run_markdown_build
from runner.tasks.export_deck import export_deck
from runner.tasks.generate_decks import run_deck_generation
from runner.tasks.helpers import get_models

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


def _dispatch_job(job_id: str) -> None:
    """Dispatch a job based on its job_type."""
    models = get_models()
    engine = create_engine(settings.database_url)
    session = Session(engine)

    with session as db:
        job = db.execute(
            select(models.Job).where(models.Job.id == UUID(job_id))
        ).scalar_one_or_none()
        if not job:
            logger.warning("job_not_found", job_id=job_id)
            return

        if job.status != "pending":
            logger.info("job_skipped", job_id=job_id, status=job.status)
            db.add(
                models.JobEvent(
                    job_id=job.id,
                    level="info",
                    message=f"Job skipped (status={job.status})",
                    step=job.current_step,
                    progress=job.progress,
                    details_json={
                        "skipped_at": datetime.utcnow().isoformat(),
                        "status": job.status,
                    },
                )
            )
            db.commit()
            return

        if job.job_type == "markdown_build":
            run_markdown_build(job_id)
            return
        if job.job_type == "deck_generation":
            run_deck_generation(job_id)
            return

        logger.warning("unknown_job_type", job_id=job_id, job_type=job.job_type)


def handle_task(payload: dict[str, Any]) -> None:
    """Dispatch a task payload to the correct handler."""
    kind = payload.get("kind")
    if kind == "job":
        job_id = payload.get("job_id")
        if not isinstance(job_id, str):
            logger.warning("missing_job_id", payload=payload)
            return
        _dispatch_job(job_id)
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

    while True:
        payload = dequeue_task(redis_conn)
        if not payload:
            continue

        try:
            logger.info("task_received", kind=payload.get("kind"))
            handle_task(payload)
        except Exception as exc:
            # Never crash the entire worker on a single task failure.
            # The task itself is responsible for transitioning DB state to failed.
            logger.exception("task_failed", error=str(exc))


if __name__ == "__main__":
    main()
