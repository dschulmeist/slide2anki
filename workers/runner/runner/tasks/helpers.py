"""Shared helpers for worker tasks."""

from __future__ import annotations

import json
import sys
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from minio import Minio
from minio.error import S3Error
from redis import Redis
from slide2anki_core.model_adapters.google import GoogleAdapter
from slide2anki_core.model_adapters.ollama import OllamaAdapter
from slide2anki_core.model_adapters.openai import OpenAIAdapter
from slide2anki_core.model_adapters.xai import XAIAdapter
from sqlalchemy.orm import Session

from runner.config import settings

QUEUE_PROGRESS_PREFIX = "slide2anki:progress"

# Global checkpointer connection (reused across jobs for efficiency)
_checkpointer_connection: Any = None


def ensure_api_on_path() -> None:
    """Ensure the API package is importable for ORM models."""
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        api_path = parent / "apps" / "api"
        if api_path.exists():
            if str(api_path) not in sys.path:
                sys.path.insert(0, str(api_path))
            return


def get_models() -> Any:
    """Load SQLAlchemy models from the API package."""
    ensure_api_on_path()
    from app.db import models  # type: ignore

    return models


def get_or_create_app_settings(db: Session, models: Any) -> Any:
    """Return the singleton application settings row, creating it if missing."""
    try:
        existing = db.query(models.AppSetting).limit(1).one_or_none()
        if existing:
            return existing

        settings_row = models.AppSetting()
        db.add(settings_row)
        db.commit()
        db.refresh(settings_row)
        return settings_row
    except Exception:
        # The worker can start before the API has initialized tables in dev.
        # In that case, fall back to environment-based configuration.
        return None


def build_model_adapter(db: Session, models: Any) -> Any:
    """Create the model adapter for the worker based on persisted app settings.

    This keeps the worker aligned with the settings chosen in the web UI (saved via the API).
    """
    app_settings = get_or_create_app_settings(db, models)

    provider = "ollama"
    model = ""
    base_url: str | None = None
    api_key: str | None = None

    if app_settings is not None:
        provider = (app_settings.provider or provider).lower()
        model = (app_settings.model or model).strip()
        base_url = (app_settings.base_url or "").strip() or None
        api_key = (app_settings.api_key or "").strip() or None

    if provider in {"openai", "openrouter"}:
        resolved_key = api_key or (settings.openai_api_key or "").strip() or None
        if not resolved_key:
            raise ValueError(f"Missing API key for provider: {provider}")

        resolved_base_url = base_url
        if provider == "openrouter" and not resolved_base_url:
            resolved_base_url = "https://openrouter.ai/api/v1"

        return OpenAIAdapter(
            api_key=resolved_key,
            base_url=resolved_base_url,
            vision_model=model or "gpt-5.2",
            text_model=model or "gpt-5.2",
        )

    if provider == "google":
        resolved_key = api_key or (settings.google_api_key or "").strip() or None
        if not resolved_key:
            raise ValueError("Missing API key for provider: google")

        return GoogleAdapter(
            api_key=resolved_key,
            vision_model=model or "gemini-3-flash-preview",
            text_model=model or "gemini-3-flash-preview",
        )

    if provider == "xai":
        resolved_key = api_key or (settings.xai_api_key or "").strip() or None
        if not resolved_key:
            raise ValueError("Missing API key for provider: xai")

        return XAIAdapter(
            api_key=resolved_key,
            vision_model=model or "grok-4-1-fast-non-reasoning",
            text_model=model or "grok-4-1-fast-non-reasoning",
        )

    if provider == "ollama":
        resolved_base_url = base_url or settings.ollama_base_url
        if not resolved_base_url:
            raise ValueError("Missing Ollama base URL")
        return OllamaAdapter(
            base_url=resolved_base_url,
            vision_model=model or "llava",
            text_model=model or "llama3",
        )

    raise ValueError(f"Unsupported provider: {provider}")


def get_minio_client() -> Minio:
    """Create a MinIO client using worker settings."""
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket(client: Minio) -> None:
    """Ensure the MinIO bucket exists for storing artifacts."""
    try:
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
    except S3Error as exc:
        if exc.code != "BucketAlreadyOwnedByYou":
            raise


def download_bytes(client: Minio, object_key: str) -> bytes:
    """Download bytes from MinIO."""
    response = client.get_object(settings.minio_bucket, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def upload_bytes(
    client: Minio,
    object_key: str,
    data: bytes,
    content_type: str,
) -> None:
    """Upload bytes to MinIO using the configured bucket."""
    client.put_object(
        settings.minio_bucket,
        object_key,
        data=BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


def publish_progress(job_id: str, progress: int, step: str) -> None:
    """Publish progress updates to Redis for streaming clients."""
    client = Redis.from_url(settings.redis_url)
    payload = json.dumps({"progress": progress, "step": step})
    client.publish(f"{QUEUE_PROGRESS_PREFIX}:{job_id}", payload)


def record_job_event(
    db: Session,
    models: Any,
    job: Any,
    *,
    level: str,
    message: str,
    step: str | None,
    progress: int | None,
    details: dict | None = None,
) -> None:
    """Persist an append-only event entry for a job.

    The UI depends on these events to show what is happening when a job is running,
    and to explain why a job failed (without requiring the user to tail worker logs).
    """
    db.add(
        models.JobEvent(
            job_id=job.id,
            level=level,
            message=message,
            step=step,
            progress=progress,
            details_json=details,
        )
    )


def update_job_progress(
    db: Session,
    job: Any,
    progress: int,
    step: str,
    status: str | None = None,
    *,
    event_message: str | None = None,
    event_level: str = "info",
    event_details: dict | None = None,
) -> None:
    """Persist job progress to the database and publish updates."""
    models = get_models()
    job.progress = progress
    job.current_step = step
    if status:
        job.status = status
        if status in {"completed", "failed"}:
            job.finished_at = datetime.utcnow()
    record_job_event(
        db,
        models,
        job,
        level=event_level,
        message=event_message or step,
        step=step,
        progress=progress,
        details=event_details,
    )
    db.commit()
    publish_progress(str(job.id), progress, step)


@contextmanager
def get_checkpointer() -> Generator[Any, None, None]:
    """Create a PostgreSQL checkpointer for LangGraph state persistence.

    Uses the langgraph-checkpoint-postgres package to persist graph state,
    allowing jobs to be resumed from their last checkpoint after failures.

    Yields:
        PostgresSaver instance configured with the database connection
    """
    global _checkpointer_connection

    try:
        import psycopg
        from langgraph.checkpoint.postgres import PostgresSaver

        # Create connection if not already established
        if _checkpointer_connection is None:
            # Convert SQLAlchemy URL to psycopg format
            db_url = settings.database_url
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
            elif db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)

            # Extract connection params from URL
            # psycopg expects a connection string without the driver prefix
            conn_str = settings.database_url
            _checkpointer_connection = psycopg.connect(conn_str)

        checkpointer = PostgresSaver(_checkpointer_connection)
        # Ensure checkpoint tables exist
        checkpointer.setup()
        yield checkpointer

    except ImportError as e:
        # Fallback to no checkpointing if package not installed
        import structlog

        logger = structlog.get_logger()
        logger.warning(
            "langgraph-checkpoint-postgres not available, checkpointing disabled",
            error=str(e),
        )
        yield None
    except Exception as e:
        import structlog

        logger = structlog.get_logger()
        logger.warning("Failed to create checkpointer", error=str(e))
        yield None


def get_checkpoint_config(job_id: str) -> dict[str, Any]:
    """Create the LangGraph config dict for a job's checkpoint.

    Args:
        job_id: The job ID to use as thread_id

    Returns:
        Config dict with thread_id set for checkpointing
    """
    return {
        "configurable": {
            "thread_id": job_id,
        }
    }
