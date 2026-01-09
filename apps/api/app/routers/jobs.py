from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.session import get_db
from app.schemas.api import JobCreate, JobResponse, JobListResponse
from app.services.queue import enqueue_job

router = APIRouter()


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    deck_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """List jobs, optionally filtered by deck."""
    query = select(models.Job).order_by(models.Job.created_at.desc())
    if deck_id:
        query = query.where(models.Job.deck_id == deck_id)
    result = await db.execute(query)
    jobs = result.scalars().all()
    return JobListResponse(jobs=[JobResponse.model_validate(j) for j in jobs])


@router.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(
    job: JobCreate,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Create and enqueue a new processing job."""
    # Verify deck exists
    result = await db.execute(
        select(models.Deck).where(models.Deck.id == job.deck_id)
    )
    deck = result.scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    # Create job record
    db_job = models.Job(
        deck_id=job.deck_id,
        status="pending",
        progress=0,
    )
    db.add(db_job)
    await db.commit()
    await db.refresh(db_job)

    # Enqueue for processing
    await enqueue_job(str(db_job.id))

    return JobResponse.model_validate(db_job)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Get job status and progress."""
    result = await db.execute(
        select(models.Job).where(models.Job.id == job_id)
    )
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
    result = await db.execute(
        select(models.Job).where(models.Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")
    job.status = "cancelled"
    await db.commit()
