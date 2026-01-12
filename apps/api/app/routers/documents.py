"""Document upload and listing routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.session import get_db
from app.schemas.api import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.queue import enqueue_job
from app.services.storage import upload_file

router = APIRouter()


@router.get(
    "/projects/{project_id}/documents",
    response_model=DocumentListResponse,
)
async def list_documents(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """List documents for a project."""
    result = await db.execute(
        select(models.Document)
        .where(models.Document.project_id == project_id)
        .order_by(models.Document.created_at.desc())
    )
    documents = result.scalars().all()
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in documents]
    )


@router.post(
    "/projects/{project_id}/documents",
    response_model=DocumentUploadResponse,
)
async def upload_document(
    project_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload a document to a project and enqueue markdown build."""
    project = await db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    content = await file.read()
    object_key = f"projects/{project_id}/documents/{file.filename}"
    await upload_file(object_key, content, content_type="application/pdf")

    document = models.Document(
        project_id=project_id,
        filename=file.filename,
        object_key=object_key,
        page_count=0,
    )
    db.add(document)
    await db.flush()

    job = models.Job(
        project_id=project_id,
        document_id=document.id,
        job_type="markdown_build",
        status="pending",
        progress=0,
        current_step="queued",
    )
    db.add(job)
    await db.commit()
    await db.refresh(document)
    await db.refresh(job)

    await enqueue_job(str(job.id))

    return DocumentUploadResponse(
        document_id=document.id,
        project_id=project_id,
        filename=document.filename,
        object_key=document.object_key,
        job_id=job.id,
    )
