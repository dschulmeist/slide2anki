"""Deck management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.session import get_db
from app.schemas.api import DeckGenerationRequest, DeckListResponse, DeckResponse
from app.services.queue import enqueue_job

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
    pending_result = await db.execute(
        select(func.count(models.CardDraft.id)).where(
            models.CardDraft.deck_id == deck_id,
            models.CardDraft.status == "pending",
        )
    )
    return total_result.scalar_one(), pending_result.scalar_one()


@router.get("/decks", response_model=DeckListResponse)
async def list_decks(
    project_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> DeckListResponse:
    """List decks, optionally filtered by project."""
    query = select(models.Deck).order_by(models.Deck.created_at.desc())
    if project_id:
        query = query.where(models.Deck.project_id == project_id)

    result = await db.execute(query)
    decks = result.scalars().all()

    deck_responses = []
    for deck in decks:
        total_cards, pending_cards = await _load_deck_counts(db, deck.id)
        deck_responses.append(
            DeckResponse(
                id=deck.id,
                project_id=deck.project_id,
                chapter_id=deck.chapter_id,
                name=deck.name,
                status=deck.status,
                created_at=deck.created_at,
                card_count=total_cards,
                pending_review=pending_cards,
            )
        )
    return DeckListResponse(decks=deck_responses)


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
        project_id=deck.project_id,
        chapter_id=deck.chapter_id,
        name=deck.name,
        status=deck.status,
        created_at=deck.created_at,
        card_count=total_cards,
        pending_review=pending_cards,
    )


@router.post(
    "/projects/{project_id}/decks/generate",
    response_model=DeckListResponse,
)
async def generate_decks(
    project_id: UUID,
    payload: DeckGenerationRequest,
    db: AsyncSession = Depends(get_db),
) -> DeckListResponse:
    """Generate decks from selected chapters."""
    project = await db.get(models.Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    chapters = (
        (
            await db.execute(
                select(models.Chapter).where(
                    models.Chapter.project_id == project_id,
                    models.Chapter.id.in_(payload.chapter_ids),
                )
            )
        )
        .scalars()
        .all()
    )

    if len(chapters) != len(payload.chapter_ids):
        raise HTTPException(status_code=400, detail="Invalid chapter selection")

    created_decks: list[models.Deck] = []
    jobs: list[models.Job] = []

    for chapter in chapters:
        config = models.GenerationConfig(
            project_id=project_id,
            chapter_id=chapter.id,
            max_cards=payload.max_cards,
            focus_json=payload.focus,
            custom_instructions=payload.custom_instructions,
        )
        db.add(config)
        await db.flush()

        deck = models.Deck(
            project_id=project_id,
            chapter_id=chapter.id,
            generation_config_id=config.id,
            name=chapter.title,
            status="processing",
        )
        db.add(deck)
        await db.flush()

        job = models.Job(
            project_id=project_id,
            deck_id=deck.id,
            job_type="deck_generation",
            status="pending",
            progress=0,
            current_step="queued",
        )
        db.add(job)

        created_decks.append(deck)
        jobs.append(job)

    await db.commit()

    for job in jobs:
        await enqueue_job(str(job.id))

    responses: list[DeckResponse] = []
    for deck in created_decks:
        responses.append(
            DeckResponse(
                id=deck.id,
                project_id=deck.project_id,
                chapter_id=deck.chapter_id,
                name=deck.name,
                status=deck.status,
                created_at=deck.created_at,
                card_count=0,
                pending_review=0,
            )
        )

    return DeckListResponse(decks=responses)
