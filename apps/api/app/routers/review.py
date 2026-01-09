"""Review routes for cards and slides."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.session import get_db
from app.schemas.api import (
    CardDraftResponse,
    CardDraftListResponse,
    CardDraftUpdate,
    SlideResponse,
    SlideListResponse,
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
    """Update a card draft (edit content, approve, reject)."""
    result = await db.execute(
        select(models.CardDraft).where(models.CardDraft.id == card_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    # Apply updates
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(card, key, value)

    await db.commit()
    await db.refresh(card)
    return CardDraftResponse.model_validate(card)


@router.get("/decks/{deck_id}/slides", response_model=SlideListResponse)
async def list_slides(
    deck_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> SlideListResponse:
    """List slides for a deck."""
    result = await db.execute(
        select(models.Slide)
        .where(models.Slide.deck_id == deck_id)
        .order_by(models.Slide.page_index)
    )
    slides = result.scalars().all()
    slide_responses = []
    for slide in slides:
        slide_responses.append(
            SlideResponse(
                id=slide.id,
                deck_id=slide.deck_id,
                page_index=slide.page_index,
                image_object_key=slide.image_object_key,
                image_url=await get_presigned_url(slide.image_object_key),
            )
        )
    return SlideListResponse(slides=slide_responses)
