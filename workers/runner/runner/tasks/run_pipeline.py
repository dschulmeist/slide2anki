"""Task for running the card generation pipeline."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

import structlog
from minio import Minio
from minio.error import S3Error
from redis import Redis
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from runner.config import settings
from slide2anki_core.graph import build_graph
from slide2anki_core.model_adapters.ollama import OllamaAdapter
from slide2anki_core.model_adapters.openai import OpenAIAdapter
from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim

logger = structlog.get_logger()

QUEUE_PROGRESS_PREFIX = "slide2anki:progress"


def _ensure_api_on_path() -> None:
    """Ensure the API package is importable for ORM models."""
    project_root = Path(__file__).resolve().parents[4]
    api_path = project_root / "apps" / "api"
    if api_path.exists() and str(api_path) not in sys.path:
        sys.path.insert(0, str(api_path))


def _get_models() -> Any:
    """Load SQLAlchemy models from the API package."""
    _ensure_api_on_path()
    from app.db import models  # type: ignore

    return models


def _get_minio_client() -> Minio:
    """Create a MinIO client using worker settings."""
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def _ensure_bucket(client: Minio) -> None:
    """Ensure the MinIO bucket exists for storing artifacts."""
    try:
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
    except S3Error as exc:
        if exc.code != "BucketAlreadyOwnedByYou":
            raise


def _download_pdf(client: Minio, object_key: str) -> bytes:
    """Download the PDF bytes from MinIO."""
    response = client.get_object(settings.minio_bucket, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def _upload_bytes(
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


def _publish_progress(job_id: str, progress: int, step: str) -> None:
    """Publish progress updates to Redis for streaming clients."""
    client = Redis.from_url(settings.redis_url)
    payload = json.dumps({"progress": progress, "step": step})
    client.publish(f"{QUEUE_PROGRESS_PREFIX}:{job_id}", payload)


def _update_job_progress(
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
    _publish_progress(str(job.id), progress, step)


async def _run_graph(
    pdf_data: bytes,
    deck_name: str,
    adapter: Any,
) -> dict[str, Any]:
    """Run the LangGraph pipeline asynchronously."""
    graph = build_graph(adapter)
    return await graph.ainvoke(
        {
            "pdf_data": pdf_data,
            "deck_name": deck_name,
        }
    )


def _build_adapter() -> Any:
    """Select the model adapter based on available settings."""
    if settings.openai_api_key:
        return OpenAIAdapter(api_key=settings.openai_api_key)
    return OllamaAdapter(base_url=settings.ollama_base_url)


def run_pipeline(job_id: str) -> dict[str, Any]:
    """
    Run the card generation pipeline for a job.

    This task:
    1. Downloads the PDF from MinIO
    2. Runs the LangGraph pipeline
    3. Stores slides, claims, and cards in the database

    Args:
        job_id: The job ID for progress tracking

    Returns:
        Summary of processing results
    """
    models = _get_models()
    logger.info("pipeline_started", job_id=job_id)

    engine = create_engine(settings.database_url)
    minio_client = _get_minio_client()
    _ensure_bucket(minio_client)

    with Session(engine) as db:
        job = db.execute(
            select(models.Job).where(models.Job.id == UUID(job_id))
        ).scalar_one_or_none()
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        try:
            if not job.upload_id:
                raise ValueError(f"Job missing upload_id: {job_id}")

            upload = db.execute(
                select(models.Upload).where(models.Upload.id == job.upload_id)
            ).scalar_one_or_none()
            if not upload:
                raise ValueError(f"Upload not found: {job.upload_id}")

            deck = db.execute(
                select(models.Deck).where(models.Deck.id == job.deck_id)
            ).scalar_one_or_none()
            if not deck:
                raise ValueError(f"Deck not found: {job.deck_id}")

            _update_job_progress(db, job, 5, "Downloading PDF", status="running")
            pdf_data = _download_pdf(minio_client, upload.pdf_object_key)

            _update_job_progress(db, job, 15, "Running pipeline")
            adapter = _build_adapter()
            result = asyncio.run(_run_graph(pdf_data, deck.name, adapter))

            slides = result.get("slides", [])
            claims: list[Claim] = result.get("claims", [])
            cards: list[CardDraft] = result.get("cards", [])

            _update_job_progress(db, job, 80, "Saving results")

            upload.page_count = len(slides)
            deck.status = "ready"

            slide_records = []
            for slide in slides:
                image_key = f"slides/{deck.id}/{upload.id}/{slide.page_index}.png"
                if slide.image_data:
                    _upload_bytes(
                        minio_client,
                        image_key,
                        slide.image_data,
                        content_type="image/png",
                    )
                slide_records.append(
                    models.Slide(
                        deck_id=deck.id,
                        page_index=slide.page_index,
                        image_object_key=image_key,
                    )
                )

            db.add_all(slide_records)
            db.flush()

            slide_id_by_index = {slide.page_index: slide.id for slide in slide_records}

            claim_records = []
            for claim in claims:
                slide_id = slide_id_by_index.get(claim.evidence.slide_index)
                if not slide_id:
                    continue
                claim_records.append(
                    models.Claim(
                        slide_id=slide_id,
                        kind=claim.kind.value,
                        statement=claim.statement,
                        confidence=claim.confidence,
                        evidence_json=claim.evidence.model_dump(),
                    )
                )

            db.add_all(claim_records)

            card_records = []
            for card in cards:
                evidence_json = [evidence.model_dump() for evidence in card.evidence]
                card_records.append(
                    models.CardDraft(
                        deck_id=deck.id,
                        front=card.front,
                        back=card.back,
                        tags=card.tags,
                        confidence=card.confidence,
                        flags_json=[flag.value for flag in card.flags],
                        evidence_json=evidence_json,
                        status="pending",
                    )
                )

            db.add_all(card_records)
            db.commit()

            _update_job_progress(db, job, 100, "Complete", status="completed")
            logger.info(
                "pipeline_completed",
                job_id=job_id,
                deck_id=str(deck.id),
                cards_generated=len(card_records),
                slides_processed=len(slide_records),
            )

            return {
                "job_id": job_id,
                "deck_id": str(deck.id),
                "status": "completed",
                "cards_generated": len(card_records),
                "slides_processed": len(slide_records),
            }
        except Exception as exc:
            deck_id = str(job.deck_id)
            _update_job_progress(db, job, 100, "Failed", status="failed")
            logger.exception(
                "pipeline_failed",
                job_id=job_id,
                deck_id=deck_id,
                error=str(exc),
            )
            raise
