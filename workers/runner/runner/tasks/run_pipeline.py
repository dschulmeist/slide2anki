"""Task for running the card generation pipeline."""

from typing import Any
from uuid import UUID

import structlog
from rq import get_current_job
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from runner.config import settings

logger = structlog.get_logger()


def update_job_progress(
    db: Session,
    job_id: UUID,
    progress: float,
    current_step: str,
) -> None:
    """Update job progress in the database."""
    # TODO: Implement actual database update
    logger.info(
        "job_progress",
        job_id=str(job_id),
        progress=progress,
        current_step=current_step,
    )


def run_pipeline(
    job_id: str,
    deck_id: str,
    pdf_object_key: str,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Run the card generation pipeline for a deck.

    This task:
    1. Downloads the PDF from MinIO
    2. Renders each page to an image
    3. Extracts claims using vision model
    4. Writes card drafts
    5. Critiques and improves cards
    6. Deduplicates across the deck
    7. Stores results in database

    Args:
        job_id: The job ID for progress tracking
        deck_id: The deck to process
        pdf_object_key: MinIO key for the PDF file
        options: Pipeline options (max_cards_per_slide, model_backend, etc.)

    Returns:
        Summary of processing results
    """
    options = options or {}
    rq_job = get_current_job()

    logger.info(
        "pipeline_started",
        job_id=job_id,
        deck_id=deck_id,
        pdf_object_key=pdf_object_key,
        options=options,
    )

    try:
        # Create database session
        engine = create_engine(settings.database_url)

        with Session(engine) as db:
            # Step 1: Download PDF
            update_job_progress(db, UUID(job_id), 5, "Downloading PDF")
            # TODO: Download from MinIO

            # Step 2: Render pages
            update_job_progress(db, UUID(job_id), 15, "Rendering slides")
            # TODO: Use core pipeline to render

            # Step 3: Extract claims
            update_job_progress(db, UUID(job_id), 35, "Extracting claims")
            # TODO: Use core pipeline to extract

            # Step 4: Write cards
            update_job_progress(db, UUID(job_id), 55, "Writing card drafts")
            # TODO: Use core pipeline to write cards

            # Step 5: Critique cards
            update_job_progress(db, UUID(job_id), 75, "Reviewing and improving cards")
            # TODO: Use core pipeline to critique

            # Step 6: Deduplicate
            update_job_progress(db, UUID(job_id), 90, "Removing duplicates")
            # TODO: Use core pipeline to dedupe

            # Step 7: Store results
            update_job_progress(db, UUID(job_id), 95, "Saving results")
            # TODO: Store cards in database

            # Done
            update_job_progress(db, UUID(job_id), 100, "Complete")

            logger.info(
                "pipeline_completed",
                job_id=job_id,
                deck_id=deck_id,
            )

            # TODO: Return actual results
            return {
                "job_id": job_id,
                "deck_id": deck_id,
                "status": "completed",
                "cards_generated": 0,  # Placeholder
                "slides_processed": 0,  # Placeholder
            }

    except Exception as e:
        logger.exception(
            "pipeline_failed",
            job_id=job_id,
            deck_id=deck_id,
            error=str(e),
        )
        raise
