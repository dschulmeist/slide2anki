"""Shared helpers for worker tasks."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

from minio import Minio
from minio.error import S3Error
from redis import Redis
from sqlalchemy.orm import Session

from runner.config import settings

QUEUE_PROGRESS_PREFIX = "slide2anki:progress"


def ensure_api_on_path() -> None:
    """Ensure the API package is importable for ORM models."""
    project_root = Path(__file__).resolve().parents[4]
    api_path = project_root / "apps" / "api"
    if api_path.exists() and str(api_path) not in sys.path:
        sys.path.insert(0, str(api_path))


def get_models() -> Any:
    """Load SQLAlchemy models from the API package."""
    ensure_api_on_path()
    from app.db import models  # type: ignore

    return models


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


def update_job_progress(
    db: Session,
    job: Any,
    progress: int,
    step: str,
    status: Optional[str] = None,
) -> None:
    """Persist job progress to the database and publish updates."""
    job.progress = progress
    job.current_step = step
    if status:
        job.status = status
        if status in {"completed", "failed"}:
            job.finished_at = datetime.utcnow()
    db.commit()
    publish_progress(str(job.id), progress, step)
