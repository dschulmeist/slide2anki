"""Main worker process that consumes jobs from Redis queue."""

import signal
import sys
from typing import NoReturn

import structlog
from redis import Redis
from rq import Worker, Queue

from runner.config import settings

logger = structlog.get_logger()


def create_redis_connection() -> Redis:
    """Create Redis connection from settings."""
    return Redis.from_url(settings.redis_url)


def create_worker(redis_conn: Redis, queues: list[str] | None = None) -> Worker:
    """Create an RQ worker instance."""
    if queues is None:
        queues = ["default", "high", "low"]

    queue_objects = [Queue(name, connection=redis_conn) for name in queues]

    return Worker(
        queues=queue_objects,
        connection=redis_conn,
        name=f"slide2anki-worker-{settings.worker_id}",
    )


def handle_shutdown(signum: int, frame) -> NoReturn:
    """Handle shutdown signals gracefully."""
    logger.info("received_shutdown_signal", signal=signum)
    sys.exit(0)


def main() -> None:
    """Main entry point for the worker."""
    # Set up signal handlers
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    logger.info(
        "starting_worker",
        worker_id=settings.worker_id,
        redis_url=settings.redis_url,
        log_level=settings.log_level,
    )

    try:
        redis_conn = create_redis_connection()
        worker = create_worker(redis_conn)

        logger.info("worker_ready", queues=[q.name for q in worker.queues])
        worker.work(with_scheduler=True)

    except Exception as e:
        logger.exception("worker_error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
