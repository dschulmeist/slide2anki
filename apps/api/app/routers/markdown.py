"""Markdown and chapter routes."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.session import get_db
from app.schemas.api import (
    ChapterListResponse,
    ChapterResponse,
    MarkdownBlockResponse,
    MarkdownBlockUpdate,
    MarkdownVersionResponse,
)

router = APIRouter()


async def _build_project_markdown(db: AsyncSession, project_id: UUID) -> str:
    """Build full markdown content for a project from stored blocks."""
    chapters = (
        (
            await db.execute(
                select(models.Chapter)
                .where(models.Chapter.project_id == project_id)
                .order_by(models.Chapter.position_index)
            )
        )
        .scalars()
        .all()
    )

    lines: list[str] = []
    for chapter in chapters:
        lines.append(f"## {chapter.title}")
        lines.append("")

        blocks = (
            (
                await db.execute(
                    select(models.MarkdownBlock)
                    .where(models.MarkdownBlock.chapter_id == chapter.id)
                    .order_by(models.MarkdownBlock.position_index)
                )
            )
            .scalars()
            .all()
        )

        for block in blocks:
            lines.append(f"<!-- block:{block.anchor_id} -->")
            lines.append(block.content)
            lines.append("")

    return "\n".join(lines).strip() + "\n"


@router.get("/projects/{project_id}/chapters", response_model=ChapterListResponse)
async def list_chapters(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ChapterListResponse:
    """List chapters for a project."""
    result = await db.execute(
        select(models.Chapter)
        .where(models.Chapter.project_id == project_id)
        .order_by(models.Chapter.position_index)
    )
    chapters = result.scalars().all()
    return ChapterListResponse(
        chapters=[ChapterResponse.model_validate(c) for c in chapters]
    )


@router.get(
    "/projects/{project_id}/markdown",
    response_model=MarkdownVersionResponse,
)
async def get_markdown(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> MarkdownVersionResponse:
    """Return the latest markdown snapshot for a project."""
    result = await db.execute(
        select(models.MarkdownVersion)
        .where(models.MarkdownVersion.project_id == project_id)
        .order_by(models.MarkdownVersion.version.desc())
        .limit(1)
    )
    version = result.scalar_one_or_none()
    if not version:
        return MarkdownVersionResponse(
            id=UUID(int=0),
            project_id=project_id,
            version=0,
            content="",
            created_at=datetime.utcnow(),
            created_by=None,
        )
    return MarkdownVersionResponse.model_validate(version)


@router.get(
    "/projects/{project_id}/blocks",
    response_model=list[MarkdownBlockResponse],
)
async def list_blocks(
    project_id: UUID,
    chapter_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[MarkdownBlockResponse]:
    """List markdown blocks for a project."""
    query = select(models.MarkdownBlock).where(
        models.MarkdownBlock.project_id == project_id
    )
    if chapter_id:
        query = query.where(models.MarkdownBlock.chapter_id == chapter_id)
    query = query.order_by(models.MarkdownBlock.position_index)

    result = await db.execute(query)
    blocks = result.scalars().all()
    return [MarkdownBlockResponse.model_validate(b) for b in blocks]


@router.patch("/blocks/{block_id}", response_model=MarkdownBlockResponse)
async def update_block(
    block_id: UUID,
    payload: MarkdownBlockUpdate,
    db: AsyncSession = Depends(get_db),
) -> MarkdownBlockResponse:
    """Update a markdown block and version the project markdown."""
    result = await db.execute(
        select(models.MarkdownBlock).where(models.MarkdownBlock.id == block_id)
    )
    block = result.scalar_one_or_none()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    block.content = payload.content
    await db.flush()

    markdown_content = await _build_project_markdown(db, block.project_id)
    latest_version = await db.execute(
        select(func.max(models.MarkdownVersion.version)).where(
            models.MarkdownVersion.project_id == block.project_id
        )
    )
    next_version = (latest_version.scalar_one() or 0) + 1

    db.add(
        models.MarkdownVersion(
            project_id=block.project_id,
            version=next_version,
            content=markdown_content,
            created_by="user",
        )
    )
    await db.commit()
    await db.refresh(block)
    return MarkdownBlockResponse.model_validate(block)
