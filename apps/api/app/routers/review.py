"""Review routes for cards and slides."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.session import get_db
from app.schemas.api import (
    CardDraftListResponse,
    CardDraftResponse,
    CardDraftUpdate,
    SlideListResponse,
    SlideResponse,
)
from app.services.storage import get_presigned_url

router = APIRouter()


@router.get("/decks/{deck_id}/cards", response_model=CardDraftListResponse)
async def list_cards(
    deck_id: UUID,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> CardDraftListResponse:
    """List card drafts for a deck."""
    query = select(models.CardDraft).where(models.CardDraft.deck_id == deck_id)
    if status:
        query = query.where(models.CardDraft.status == status)
    result = await db.execute(query)
    cards = result.scalars().all()
    return CardDraftListResponse(
        cards=[CardDraftResponse.model_validate(c) for c in cards]
    )


@router.get("/cards/{card_id}", response_model=CardDraftResponse)
async def get_card(
    card_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CardDraftResponse:
    """Get a specific card draft."""
    result = await db.execute(
        select(models.CardDraft).where(models.CardDraft.id == card_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return CardDraftResponse.model_validate(card)


@router.patch("/cards/{card_id}", response_model=CardDraftResponse)
async def update_card(
    card_id: UUID,
    updates: CardDraftUpdate,
    db: AsyncSession = Depends(get_db),
) -> CardDraftResponse:
    """Update a card draft and append a revision entry."""
    result = await db.execute(
        select(models.CardDraft).where(models.CardDraft.id == card_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(card, key, value)

    revision_number = await db.execute(
        select(func.max(models.CardRevision.revision_number)).where(
            models.CardRevision.card_id == card.id
        )
    )
    next_revision = (revision_number.scalar_one() or 0) + 1

    db.add(
        models.CardRevision(
            card_id=card.id,
            revision_number=next_revision,
            front=card.front,
            back=card.back,
            tags=card.tags or [],
            edited_by="user",
        )
    )

    await db.commit()
    await db.refresh(card)
    return CardDraftResponse.model_validate(card)


@router.get("/projects/{project_id}/slides", response_model=SlideListResponse)
async def list_slides(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SlideListResponse:
    """List slides for a project."""
    result = await db.execute(
        select(models.Slide)
        .join(models.Document, models.Slide.document_id == models.Document.id)
        .where(models.Document.project_id == project_id)
        .order_by(models.Slide.document_id, models.Slide.page_index)
    )
    slides = result.scalars().all()
    slide_responses = []
    for slide in slides:
        slide_responses.append(
            SlideResponse(
                id=slide.id,
                document_id=slide.document_id,
                page_index=slide.page_index,
                image_object_key=slide.image_object_key,
                image_url=await get_presigned_url(slide.image_object_key),
            )
        )
    return SlideListResponse(slides=slide_responses)
