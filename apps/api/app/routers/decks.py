from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db import models
from app.schemas.api import DeckCreate, DeckResponse, DeckListResponse
from sqlalchemy import select

router = APIRouter()


@router.get("/decks", response_model=DeckListResponse)
async def list_decks(
    db: AsyncSession = Depends(get_db),
) -> DeckListResponse:
    """List all decks."""
    result = await db.execute(
        select(models.Deck).order_by(models.Deck.created_at.desc())
    )
    decks = result.scalars().all()
    return DeckListResponse(
        decks=[DeckResponse.model_validate(d) for d in decks]
    )


@router.post("/decks", response_model=DeckResponse, status_code=201)
async def create_deck(
    deck: DeckCreate,
    db: AsyncSession = Depends(get_db),
) -> DeckResponse:
    """Create a new deck."""
    db_deck = models.Deck(name=deck.name)
    db.add(db_deck)
    await db.commit()
    await db.refresh(db_deck)
    return DeckResponse.model_validate(db_deck)


@router.get("/decks/{deck_id}", response_model=DeckResponse)
async def get_deck(
    deck_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DeckResponse:
    """Get a specific deck by ID."""
    result = await db.execute(
        select(models.Deck).where(models.Deck.id == deck_id)
    )
    deck = result.scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    return DeckResponse.model_validate(deck)


@router.delete("/decks/{deck_id}", status_code=204)
async def delete_deck(
    deck_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a deck and all associated data."""
    result = await db.execute(
        select(models.Deck).where(models.Deck.id == deck_id)
    )
    deck = result.scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    await db.delete(deck)
    await db.commit()
