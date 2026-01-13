"""Task for building the canonical markdown knowledge base.

This module executes the document processing pipeline to extract educational
content from uploaded PDF documents. It supports two pipeline modes:

Holistic Pipeline (Default):
    Processes documents as coherent units with chunked extraction (15% overlap).
    Produces higher quality markdown with natural deduplication.
    Controlled by `settings.use_holistic_pipeline` (default: True).

Legacy Pipeline:
    Per-slide extraction with region segmentation.
    May produce redundant content on metadata-heavy documents.
    Available by setting `use_holistic_pipeline=False`.

The task persists results to the database including:
- Rendered slide images (uploaded to MinIO)
- Extracted claims (linked to source slides)
- Markdown blocks (deduplicated across the project)
- Markdown version snapshot
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import structlog
from slide2anki_core.graph import (
    HolisticConfig,
    build_holistic_graph,
    build_markdown_graph,
)
from slide2anki_core.schemas.claims import Claim
from slide2anki_core.schemas.markdown import MarkdownBlock
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from runner.config import settings
from runner.tasks.helpers import (
    build_model_adapter,
    download_bytes,
    ensure_bucket,
    get_checkpoint_config,
    get_checkpointer,
    get_minio_client,
    get_models,
    update_job_progress,
    upload_bytes,
)

logger = structlog.get_logger()


def _normalize_title(filename: str) -> str:
    """Normalize a filename into a readable chapter title."""
    return Path(filename).stem.replace("_", " ").replace("-", " ").strip()


def _get_or_create_chapter(db: Session, models: Any, project_id: UUID, title: str):
    """Find or create a chapter by title for the project."""
    existing = db.execute(
        select(models.Chapter).where(
            models.Chapter.project_id == project_id,
            models.Chapter.title == title,
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    position_index = (
        db.execute(
            select(func.count(models.Chapter.id)).where(
                models.Chapter.project_id == project_id
            )
        ).scalar_one()
        or 0
    )
    chapter = models.Chapter(
        project_id=project_id, title=title, position_index=position_index
    )
    db.add(chapter)
    db.flush()
    return chapter


def _build_project_markdown(db: Session, models: Any, project_id: UUID) -> str:
    """Build full markdown content for a project from stored blocks."""
    chapters = db.execute(
        select(models.Chapter)
        .where(models.Chapter.project_id == project_id)
        .order_by(models.Chapter.position_index)
    ).scalars()

    lines: list[str] = []
    for chapter in chapters:
        lines.append(f"## {chapter.title}")
        lines.append("")

        blocks = (
            db.execute(
                select(models.MarkdownBlock)
                .where(models.MarkdownBlock.chapter_id == chapter.id)
                .order_by(models.MarkdownBlock.position_index)
            )
            .scalars()
            .all()
        )
        for block in blocks:
            lines.append(f"<!-- block:{block.anchor_id} -->")
            lines.append(block.content)
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def _persist_claims(
    db: Session,
    models: Any,
    claims: list[Claim],
    slide_id_by_index: dict[int, UUID],
    document_id: UUID,
) -> None:
    """Persist extracted claims to the database."""
    for claim in claims:
        slide_id = slide_id_by_index.get(claim.evidence.slide_index)
        if not slide_id:
            continue
        evidence = claim.evidence.model_copy(update={"document_id": str(document_id)})
        db.add(
            models.Claim(
                slide_id=slide_id,
                kind=claim.kind.value,
                statement=claim.statement,
                confidence=claim.confidence,
                evidence_json=evidence.model_dump(),
            )
        )


def _persist_blocks(
    db: Session,
    models: Any,
    blocks: list[MarkdownBlock],
    project_id: UUID,
    chapter_id: UUID,
    document_id: UUID,
) -> None:
    """Persist markdown blocks with deduplication across the project."""
    for block in blocks:
        existing = db.execute(
            select(models.MarkdownBlock).where(
                models.MarkdownBlock.project_id == project_id,
                models.MarkdownBlock.anchor_id == block.anchor_id,
            )
        ).scalar_one_or_none()

        evidence_json = [
            evidence.model_copy(update={"document_id": str(document_id)}).model_dump()
            for evidence in block.evidence
        ]

        if existing:
            # Preserve earliest position; append evidence for traceability.
            existing_evidence = existing.evidence_json or []
            existing.evidence_json = existing_evidence + evidence_json
            db.add(existing)
            continue

        db.add(
            models.MarkdownBlock(
                project_id=project_id,
                chapter_id=chapter_id,
                anchor_id=block.anchor_id,
                kind=block.kind,
                content=block.content,
                evidence_json=evidence_json,
                position_index=block.position_index,
            )
        )


def run_markdown_build(job_id: str) -> dict[str, Any]:
    """Run the markdown build pipeline for a document job."""
    models = get_models()
    logger.info("markdown_build_started", job_id=job_id)

    engine = create_engine(settings.database_url)
    session = Session(engine)

    minio_client = get_minio_client()
    ensure_bucket(minio_client)

    with session as db:
        job = db.execute(
            select(models.Job).where(models.Job.id == UUID(job_id))
        ).scalar_one_or_none()
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        try:
            if job.job_type != "markdown_build":
                raise ValueError(f"Unexpected job type: {job.job_type}")
            if not job.document_id:
                raise ValueError("Job missing document_id")

            document = db.execute(
                select(models.Document).where(models.Document.id == job.document_id)
            ).scalar_one_or_none()
            if not document:
                raise ValueError(f"Document not found: {job.document_id}")

            project = db.execute(
                select(models.Project).where(models.Project.id == job.project_id)
            ).scalar_one_or_none()
            if not project:
                raise ValueError(f"Project not found: {job.project_id}")

            update_job_progress(db, job, 5, "Downloading document", status="running")
            pdf_data = download_bytes(minio_client, document.object_key)

            update_job_progress(db, job, 15, "Running markdown pipeline")
            adapter = build_model_adapter(db, models)

            # Select pipeline: holistic (recommended) or legacy
            # Holistic pipeline processes documents as coherent units for higher quality
            use_holistic = getattr(settings, "use_holistic_pipeline", True)

            with get_checkpointer() as checkpointer:
                checkpoint_config = get_checkpoint_config(job_id)

                if use_holistic:
                    logger.info(
                        "using_holistic_pipeline",
                        job_id=job_id,
                        document_id=str(document.id),
                    )
                    holistic_config = HolisticConfig(
                        chunk_size=10,
                        chunk_overlap=0.15,
                    )
                    graph = build_holistic_graph(
                        adapter,
                        config=holistic_config,
                        checkpointer=checkpointer,
                    )
                else:
                    logger.info(
                        "using_legacy_pipeline",
                        job_id=job_id,
                        document_id=str(document.id),
                    )
                    graph = build_markdown_graph(adapter, checkpointer=checkpointer)

                result = asyncio.run(
                    graph.ainvoke(
                        {
                            "pdf_data": pdf_data,
                            "deck_name": _normalize_title(document.filename),
                        },
                        config=checkpoint_config,
                    )
                )

            errors = [str(error) for error in result.get("errors", []) if error]
            if errors:
                raise RuntimeError(f"Markdown pipeline error: {errors[0]}")

            slides = result.get("slides", [])
            if not slides:
                raise RuntimeError("Markdown pipeline produced no slides")

            claims: list[Claim] = result.get("claims", [])
            blocks: list[MarkdownBlock] = result.get("markdown_blocks", [])

            update_job_progress(db, job, 60, "Saving slides and claims")

            existing_slides = (
                db.execute(
                    select(models.Slide).where(models.Slide.document_id == document.id)
                )
                .scalars()
                .all()
            )
            for slide in existing_slides:
                db.delete(slide)
            db.flush()

            slide_records = []
            for slide in slides:
                image_key = (
                    f"projects/{project.id}/documents/{document.id}/"
                    f"slides/{slide.page_index}.png"
                )
                if slide.image_data:
                    upload_bytes(
                        minio_client,
                        image_key,
                        slide.image_data,
                        content_type="image/png",
                    )
                slide_records.append(
                    models.Slide(
                        document_id=document.id,
                        page_index=slide.page_index,
                        image_object_key=image_key,
                    )
                )

            db.add_all(slide_records)
            db.flush()

            slide_id_by_index = {slide.page_index: slide.id for slide in slide_records}
            _persist_claims(
                db,
                models,
                claims,
                slide_id_by_index,
                document.id,
            )

            update_job_progress(db, job, 80, "Saving markdown")

            chapter_title = _normalize_title(document.filename)
            chapter = _get_or_create_chapter(db, models, project.id, chapter_title)

            existing_blocks = (
                db.execute(
                    select(models.MarkdownBlock).where(
                        models.MarkdownBlock.chapter_id == chapter.id
                    )
                )
                .scalars()
                .all()
            )
            for block in existing_blocks:
                db.delete(block)
            db.flush()

            _persist_blocks(db, models, blocks, project.id, chapter.id, document.id)

            markdown_content = _build_project_markdown(db, models, project.id)
            latest_version = db.execute(
                select(func.max(models.MarkdownVersion.version)).where(
                    models.MarkdownVersion.project_id == project.id
                )
            ).scalar_one()
            next_version = (latest_version or 0) + 1

            db.add(
                models.MarkdownVersion(
                    project_id=project.id,
                    version=next_version,
                    content=markdown_content,
                    created_by="system",
                )
            )
            document.page_count = len(slides)
            project.updated_at = datetime.utcnow()

            db.commit()

            update_job_progress(db, job, 100, "Complete", status="completed")
            logger.info(
                "markdown_build_completed",
                job_id=job_id,
                project_id=str(project.id),
                document_id=str(document.id),
                blocks=len(blocks),
            )

            return {
                "job_id": job_id,
                "project_id": str(project.id),
                "document_id": str(document.id),
                "status": "completed",
                "blocks": len(blocks),
            }
        except Exception as exc:
            job.error_message = str(exc)
            update_job_progress(db, job, 100, "Failed", status="failed")
            logger.exception(
                "markdown_build_failed",
                job_id=job_id,
                error=str(exc),
            )
            raise
