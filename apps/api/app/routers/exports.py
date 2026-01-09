from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.session import get_db
from app.schemas.api import ExportRequest, ExportResponse, ExportListResponse

router = APIRouter()


@router.post("/decks/{deck_id}/export", response_model=ExportResponse)
async def export_deck(
    deck_id: UUID,
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
) -> ExportResponse:
    """Export approved cards from a deck."""
    # Verify deck exists
    result = await db.execute(
        select(models.Deck).where(models.Deck.id == deck_id)
    )
    deck = result.scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    # Get approved cards
    cards_result = await db.execute(
        select(models.CardDraft)
        .where(models.CardDraft.deck_id == deck_id)
        .where(models.CardDraft.status == "approved")
    )
    cards = cards_result.scalars().all()

    if not cards:
        raise HTTPException(status_code=400, detail="No approved cards to export")

    # Generate export
    object_key = f"exports/{deck_id}/{deck.name}.{request.format}"

    # Create export record
    export = models.Export(
        deck_id=deck_id,
        type=request.format,
        object_key=object_key,
    )
    db.add(export)
    await db.commit()
    await db.refresh(export)

    # TODO: Actually generate and upload the export file
    # For now, just return the record

    return ExportResponse(
        export_id=export.id,
        deck_id=deck_id,
        format=request.format,
        download_url=f"/api/v1/exports/{export.id}/download",
        card_count=len(cards),
    )


@router.get("/decks/{deck_id}/exports", response_model=ExportListResponse)
async def list_exports(
    deck_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ExportListResponse:
    """List exports for a deck."""
    result = await db.execute(
        select(models.Export)
        .where(models.Export.deck_id == deck_id)
        .order_by(models.Export.created_at.desc())
    )
    exports = result.scalars().all()
    return ExportListResponse(
        exports=[
            ExportResponse(
                export_id=e.id,
                deck_id=e.deck_id,
                format=e.type,
                download_url=f"/api/v1/exports/{e.id}/download",
                card_count=0,  # TODO: Get actual count
            )
            for e in exports
        ]
    )


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Get a signed download URL for an export."""
    result = await db.execute(
        select(models.Export).where(models.Export.id == export_id)
    )
    export = result.scalar_one_or_none()
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")

    # TODO: Generate signed URL from MinIO
    return {"download_url": f"http://localhost:9000/{export.object_key}"}
