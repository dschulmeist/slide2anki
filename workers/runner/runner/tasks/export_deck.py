"""Task for exporting decks to various formats."""

from __future__ import annotations

import sys
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID

import structlog
from minio import Minio
from minio.error import S3Error
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from runner.config import settings
from slide2anki_core.exporters.apkg import export_apkg
from slide2anki_core.exporters.tsv import export_tsv
from slide2anki_core.schemas.cards import CardDraft, CardStatus

logger = structlog.get_logger()


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
    """Ensure the MinIO bucket exists for storing exports."""
    try:
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
    except S3Error as exc:
        if exc.code != "BucketAlreadyOwnedByYou":
            raise


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


def _build_card_drafts(rows: list[Any]) -> list[CardDraft]:
    """Convert database rows into core CardDraft objects."""
    drafts: list[CardDraft] = []
    for row in rows:
        drafts.append(
            CardDraft(
                front=row.front,
                back=row.back,
                tags=row.tags or [],
                confidence=row.confidence,
                status=CardStatus.APPROVED,
            )
        )
    return drafts


def export_deck(export_id: str) -> dict[str, Any]:
    """
    Export a deck to the specified format.

    Args:
        export_id: The export record ID

    Returns:
        Export result with object key
    """
    models = _get_models()
    logger.info("export_started", export_id=export_id)

    engine = create_engine(settings.database_url)
    minio_client = _get_minio_client()
    _ensure_bucket(minio_client)

    with Session(engine) as db:
        try:
            export = db.execute(
                select(models.Export).where(models.Export.id == UUID(export_id))
            ).scalar_one_or_none()
            if not export:
                raise ValueError(f"Export not found: {export_id}")

            deck = db.execute(
                select(models.Deck).where(models.Deck.id == export.deck_id)
            ).scalar_one_or_none()
            if not deck:
                raise ValueError(f"Deck not found: {export.deck_id}")

            cards_result = db.execute(
                select(models.CardDraft).where(
                    models.CardDraft.deck_id == export.deck_id,
                    models.CardDraft.status == "approved",
                )
            )
            cards = cards_result.scalars().all()
            card_drafts = _build_card_drafts(cards)

            if export.type == "tsv":
                content = export_tsv(card_drafts)
                _upload_bytes(
                    minio_client,
                    export.object_key,
                    content.encode("utf-8"),
                    content_type="text/tab-separated-values",
                )

            elif export.type == "apkg":
                with tempfile.TemporaryDirectory() as temp_dir:
                    output_path = Path(temp_dir) / f"{deck.name}.apkg"
                    export_apkg(card_drafts, deck.name, output_path)
                    data = output_path.read_bytes()
                    _upload_bytes(
                        minio_client,
                        export.object_key,
                        data,
                        content_type="application/octet-stream",
                    )
            else:
                raise ValueError(f"Unknown export type: {export.type}")

            logger.info(
                "export_completed",
                export_id=export_id,
                deck_id=str(deck.id),
                object_key=export.object_key,
            )

            return {
                "export_id": export_id,
                "deck_id": str(deck.id),
                "object_key": export.object_key,
                "status": "completed",
            }
        except Exception as exc:
            logger.exception(
                "export_failed",
                export_id=export_id,
                error=str(exc),
            )
            raise
