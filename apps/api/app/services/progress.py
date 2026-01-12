"""Progress tracking helpers for jobs."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.services.queue import publish_progress


async def update_job_progress(
    db: AsyncSession,
    job_id: str,
    progress: int,
    step: str,
    status: str | None = None,
) -> None:
    """Update job progress in database and publish to Redis."""
    from uuid import UUID

    result = await db.execute(select(models.Job).where(models.Job.id == UUID(job_id)))
    job = result.scalar_one_or_none()

    if job:
        job.progress = progress
        job.current_step = step
        if status:
            job.status = status
            if status in ("completed", "failed"):
                job.finished_at = datetime.utcnow()
        await db.commit()

    # Publish to Redis for real-time updates
    await publish_progress(job_id, progress, step)
