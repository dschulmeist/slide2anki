"""Project management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.session import get_db
from app.schemas.api import ProjectCreate, ProjectListResponse, ProjectResponse

router = APIRouter()


async def _load_project_counts(
    db: AsyncSession,
    project_id: UUID,
) -> tuple[int, int]:
    """Return document and deck counts for a project."""
    document_count = await db.execute(
        select(func.count(models.Document.id)).where(
            models.Document.project_id == project_id
        )
    )
    deck_count = await db.execute(
        select(func.count(models.Deck.id)).where(
            models.Deck.project_id == project_id
        )
    )
    return document_count.scalar_one(), deck_count.scalar_one()


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    db: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    """List all projects."""
    result = await db.execute(
        select(models.Project).order_by(models.Project.created_at.desc())
    )
    projects = result.scalars().all()

    responses: list[ProjectResponse] = []
    for project in projects:
        document_count, deck_count = await _load_project_counts(db, project.id)
        responses.append(
            ProjectResponse(
                id=project.id,
                name=project.name,
                created_at=project.created_at,
                updated_at=project.updated_at,
                document_count=document_count,
                deck_count=deck_count,
            )
        )
    return ProjectListResponse(projects=responses)


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Create a new project."""
    project = models.Project(name=payload.name)
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        created_at=project.created_at,
        updated_at=project.updated_at,
        document_count=0,
        deck_count=0,
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Get a single project by ID."""
    result = await db.execute(
        select(models.Project).where(models.Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    document_count, deck_count = await _load_project_counts(db, project.id)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        created_at=project.created_at,
        updated_at=project.updated_at,
        document_count=document_count,
        deck_count=deck_count,
    )
