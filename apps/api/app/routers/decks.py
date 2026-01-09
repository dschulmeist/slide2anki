"""Deck management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db import models
from app.schemas.api import DeckCreate, DeckResponse, DeckListResponse
from sqlalchemy import select, func

router = APIRouter()


async def _load_deck_counts(
    db: AsyncSession,
    deck_id: UUID,
) -> tuple[int, int]:
    """Return total and pending card counts for a deck."""
    total_result = await db.execute(
        select(func.count(models.CardDraft.id)).where(
            models.CardDraft.deck_id == deck_id
        )
    )
    total_cards = total_result.scalar_one()

    pending_result = await db.execute(
        select(func.count(models.CardDraft.id)).where(
            models.CardDraft.deck_id == deck_id,
            models.CardDraft.status == "pending",
        )
    )
    pending_cards = pending_result.scalar_one()

    return total_cards, pending_cards


@router.get("/decks", response_model=DeckListResponse)
async def list_decks(
    db: AsyncSession = Depends(get_db),
) -> DeckListResponse:
    """List all decks."""
    result = await db.execute(
        select(models.Deck).order_by(models.Deck.created_at.desc())
    )
    decks = result.scalars().all()
    deck_responses = []
    for deck in decks:
        total_cards, pending_cards = await _load_deck_counts(db, deck.id)
        deck_responses.append(
            DeckResponse(
                id=deck.id,
                name=deck.name,
                status=deck.status,
                created_at=deck.created_at,
                card_count=total_cards,
                pending_review=pending_cards,
            )
        )
    return DeckListResponse(decks=deck_responses)


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
    result = await db.execute(select(models.Deck).where(models.Deck.id == deck_id))
    deck = result.scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    total_cards, pending_cards = await _load_deck_counts(db, deck.id)
    return DeckResponse(
        id=deck.id,
        name=deck.name,
        status=deck.status,
        created_at=deck.created_at,
        card_count=total_cards,
        pending_review=pending_cards,
    )


@router.delete("/decks/{deck_id}", status_code=204)
async def delete_deck(
    deck_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a deck and all associated data."""
    result = await db.execute(select(models.Deck).where(models.Deck.id == deck_id))
    deck = result.scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    await db.delete(deck)
    await db.commit()
