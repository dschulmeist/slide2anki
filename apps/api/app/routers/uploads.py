"""Upload routes for deck PDFs."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.session import get_db
from app.schemas.api import UploadResponse
from app.services.queue import enqueue_pipeline_job
from app.services.storage import upload_file

router = APIRouter()


@router.post("/decks/{deck_id}/upload", response_model=UploadResponse)
async def upload_pdf(
    deck_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    """Upload a PDF file to a deck."""
    # Verify deck exists
    result = await db.execute(select(models.Deck).where(models.Deck.id == deck_id))
    deck = result.scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Upload to storage
    content = await file.read()
    object_key = f"uploads/{deck_id}/{file.filename}"
    await upload_file(object_key, content, content_type="application/pdf")

    # Create upload record
    upload = models.Upload(
        deck_id=deck_id,
        pdf_object_key=object_key,
        page_count=0,  # Will be updated after processing
    )
    db.add(upload)
    await db.flush()

    # Create a processing job tied to the upload
    job = models.Job(
        deck_id=deck_id,
        upload_id=upload.id,
        status="pending",
        progress=0,
        current_step="queued",
    )
    db.add(job)
    deck.status = "processing"

    await db.commit()
    await db.refresh(upload)
    await db.refresh(job)

    await enqueue_pipeline_job(str(job.id))

    return UploadResponse(
        upload_id=upload.id,
        deck_id=deck_id,
        filename=file.filename,
        object_key=object_key,
        job_id=job.id,
    )
