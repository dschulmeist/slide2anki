"""Task for generating decks from markdown blocks."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

import structlog
from slide2anki_core.graph import build_card_graph
from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim, ClaimKind, Evidence
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from runner.config import settings
from runner.tasks.helpers import build_model_adapter, get_models, update_job_progress

logger = structlog.get_logger()


def _strip_formula(content: str) -> str:
    """Strip markdown formula fences from content."""
    stripped = content.strip()
    if stripped.startswith("$$") and stripped.endswith("$$"):
        stripped = stripped.strip("$").strip()
    return stripped


def _build_claims(
    blocks: list[Any],
) -> tuple[list[Claim], dict[str, str]]:
    """Convert markdown blocks into claims with anchor mapping."""
    claims: list[Claim] = []
    anchor_map: dict[str, str] = {}

    for block in blocks:
        content = block.content
        if block.kind == "formula":
            content = _strip_formula(content)

        try:
            kind = ClaimKind(block.kind)
        except ValueError:
            kind = ClaimKind.OTHER
        evidence_list = block.evidence_json or []
        evidence = Evidence(slide_index=0)
        if evidence_list:
            evidence = Evidence(**evidence_list[0])

        claim = Claim(kind=kind, statement=content, confidence=1.0, evidence=evidence)
        claims.append(claim)
        anchor_map[claim.statement] = block.anchor_id

    return claims, anchor_map


def _assign_anchor_id(card: CardDraft, anchor_map: dict[str, str]) -> str | None:
    """Assign an anchor ID to a card by matching claim statements."""
    for statement, anchor_id in anchor_map.items():
        if statement in card.front or statement in card.back:
            return anchor_id
    return None


def run_deck_generation(job_id: str) -> dict[str, Any]:
    """Run deck generation for a deck job."""
    models = get_models()
    logger.info("deck_generation_started", job_id=job_id)

    engine = create_engine(settings.database_url)
    session = Session(engine)

    with session as db:
        job = db.execute(
            select(models.Job).where(models.Job.id == UUID(job_id))
        ).scalar_one_or_none()
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        try:
            if job.job_type != "deck_generation":
                raise ValueError(f"Unexpected job type: {job.job_type}")
            if not job.deck_id:
                raise ValueError("Job missing deck_id")

            deck = db.execute(
                select(models.Deck).where(models.Deck.id == job.deck_id)
            ).scalar_one_or_none()
            if not deck:
                raise ValueError(f"Deck not found: {job.deck_id}")

            chapter = None
            if deck.chapter_id:
                chapter = db.execute(
                    select(models.Chapter).where(models.Chapter.id == deck.chapter_id)
                ).scalar_one_or_none()

            config = None
            if deck.generation_config_id:
                config = db.execute(
                    select(models.GenerationConfig).where(
                        models.GenerationConfig.id == deck.generation_config_id
                    )
                ).scalar_one_or_none()

            update_job_progress(
                db, job, 10, "Preparing markdown blocks", status="running"
            )

            blocks = []
            if chapter:
                blocks = (
                    db.execute(
                        select(models.MarkdownBlock).where(
                            models.MarkdownBlock.chapter_id == chapter.id
                        )
                    )
                    .scalars()
                    .all()
                )

            claims, anchor_map = _build_claims(blocks)
            adapter = build_model_adapter(db, models)
            graph = build_card_graph(adapter)

            update_job_progress(db, job, 30, "Generating cards")
            result = asyncio.run(
                graph.ainvoke(
                    {
                        "claims": claims,
                        "max_cards": config.max_cards if config else 0,
                        "focus": config.focus_json if config else None,
                        "custom_instructions": (
                            config.custom_instructions if config else None
                        ),
                    }
                )
            )

            errors = [str(error) for error in result.get("errors", []) if error]
            if errors:
                raise RuntimeError(f"Card generation error: {errors[0]}")

            cards: list[CardDraft] = result.get("cards", [])
            if config and config.max_cards > 0:
                cards = cards[: config.max_cards]

            update_job_progress(db, job, 70, "Saving cards")

            for card in cards:
                anchor_id = _assign_anchor_id(card, anchor_map)
                db_card = models.CardDraft(
                    deck_id=deck.id,
                    anchor_id=anchor_id,
                    front=card.front,
                    back=card.back,
                    tags=card.tags,
                    confidence=card.confidence,
                    flags_json=[flag.value for flag in card.flags],
                    evidence_json=[e.model_dump() for e in card.evidence],
                    status="pending",
                )
                db.add(db_card)
                db.flush()
                db.add(
                    models.CardRevision(
                        card_id=db_card.id,
                        revision_number=1,
                        front=db_card.front,
                        back=db_card.back,
                        tags=db_card.tags or [],
                        edited_by="system",
                    )
                )

            deck.status = "ready"
            db.commit()

            update_job_progress(db, job, 100, "Complete", status="completed")
            logger.info(
                "deck_generation_completed",
                job_id=job_id,
                deck_id=str(deck.id),
                cards=len(cards),
            )

            return {
                "job_id": job_id,
                "deck_id": str(deck.id),
                "status": "completed",
                "cards": len(cards),
            }
        except Exception as exc:
            job.error_message = str(exc)
            update_job_progress(db, job, 100, "Failed", status="failed")
            logger.exception(
                "deck_generation_failed",
                job_id=job_id,
                error=str(exc),
            )
            raise
