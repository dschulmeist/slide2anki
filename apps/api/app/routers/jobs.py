"""Job management routes."""

import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.session import get_db
from app.schemas.api import (
    JobCreate,
    JobEventListResponse,
    JobEventResponse,
    JobListResponse,
    JobResponse,
)
from app.services.queue import enqueue_job, subscribe_progress

router = APIRouter()


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    project_id: Optional[UUID] = None,
    deck_id: Optional[UUID] = None,
    document_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """List jobs, optionally filtered by project, deck, or document."""
    query = select(models.Job).order_by(models.Job.created_at.desc())
    if project_id:
        query = query.where(models.Job.project_id == project_id)
    if deck_id:
        query = query.where(models.Job.deck_id == deck_id)
    if document_id:
        query = query.where(models.Job.document_id == document_id)

    result = await db.execute(query)
    jobs = result.scalars().all()
    return JobListResponse(jobs=[JobResponse.model_validate(j) for j in jobs])


@router.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(
    payload: JobCreate,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Create and enqueue a new job."""
    project = await db.get(models.Project, payload.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.job_type == "markdown_build":
        if not payload.document_id:
            raise HTTPException(status_code=400, detail="document_id is required")
        document = await db.get(models.Document, payload.document_id)
        if not document or document.project_id != project.id:
            raise HTTPException(status_code=404, detail="Document not found")
    elif payload.job_type == "deck_generation":
        if not payload.deck_id:
            raise HTTPException(status_code=400, detail="deck_id is required")
        deck = await db.get(models.Deck, payload.deck_id)
        if not deck or deck.project_id != project.id:
            raise HTTPException(status_code=404, detail="Deck not found")
    else:
        raise HTTPException(status_code=400, detail="Unsupported job type")

    job = models.Job(
        project_id=payload.project_id,
        document_id=payload.document_id,
        deck_id=payload.deck_id,
        job_type=payload.job_type,
        status="pending",
        progress=0,
        current_step="queued",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    db.add(
        models.JobEvent(
            job_id=job.id,
            level="info",
            message="Job queued",
            step=job.current_step,
            progress=job.progress,
        )
    )
    await db.commit()

    await enqueue_job(str(job.id))

    return JobResponse.model_validate(job)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Get job status and progress."""
    result = await db.execute(select(models.Job).where(models.Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)


@router.delete("/jobs/{job_id}", status_code=204)
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Cancel a pending or running job."""
    result = await db.execute(select(models.Job).where(models.Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")
    job.status = "cancelled"
    db.add(
        models.JobEvent(
            job_id=job.id,
            level="info",
            message="Job cancelled",
            step=job.current_step,
            progress=job.progress,
        )
    )
    await db.commit()


@router.get("/jobs/{job_id}/stream")
async def stream_job_progress(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream job progress updates over Server-Sent Events."""
    result = await db.execute(select(models.Job).where(models.Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        """Yield progress events in SSE format."""
        async for event in subscribe_progress(str(job_id)):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.post("/jobs/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Retry a failed or cancelled job.

    If the job has checkpoint data from a previous run, it will resume
    from the last successful checkpoint rather than starting over.
    """
    result = await db.execute(select(models.Job).where(models.Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ("failed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Only failed or cancelled jobs can be retried (current: {job.status})",
        )

    # Reset job state for retry
    job.status = "pending"
    job.progress = 0
    job.current_step = "queued"
    job.error_message = None
    job.finished_at = None

    db.add(
        models.JobEvent(
            job_id=job.id,
            level="info",
            message="Job queued for retry (will resume from checkpoint if available)",
            step=job.current_step,
            progress=job.progress,
        )
    )
    await db.commit()
    await db.refresh(job)

    await enqueue_job(str(job.id))

    return JobResponse.model_validate(job)


@router.get("/jobs/{job_id}/events", response_model=JobEventListResponse)
async def list_job_events(
    job_id: UUID,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
) -> JobEventListResponse:
    """List the most recent events for a job."""
    limit = max(1, min(limit, 500))
    result = await db.execute(select(models.Job).where(models.Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    events_result = await db.execute(
        select(models.JobEvent)
        .where(models.JobEvent.job_id == job_id)
        .order_by(models.JobEvent.created_at.desc())
        .limit(limit)
    )
    events = events_result.scalars().all()
    # Reverse for chronological display.
    events.reverse()
    return JobEventListResponse(
        events=[JobEventResponse.model_validate(event) for event in events]
    )
