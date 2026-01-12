"""Pydantic schemas for API request and response models."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    """Payload for creating a new project."""

    name: str


class ProjectResponse(BaseModel):
    """Project response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    deck_count: int = 0


class ProjectListResponse(BaseModel):
    """List response for projects."""

    projects: list[ProjectResponse]


class DocumentResponse(BaseModel):
    """Document response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    filename: str
    object_key: str
    page_count: int
    created_at: datetime


class DocumentListResponse(BaseModel):
    """List response for documents."""

    documents: list[DocumentResponse]


class DocumentUploadResponse(BaseModel):
    """Response returned after uploading a document."""

    document_id: UUID
    project_id: UUID
    filename: str
    object_key: str
    job_id: UUID


class ChapterResponse(BaseModel):
    """Chapter response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    title: str
    position_index: int


class ChapterListResponse(BaseModel):
    """List response for chapters."""

    chapters: list[ChapterResponse]


class MarkdownVersionResponse(BaseModel):
    """Markdown version response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    version: int
    content: str
    created_at: datetime
    created_by: Optional[str] = None


class MarkdownBlockResponse(BaseModel):
    """Markdown block response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    chapter_id: UUID
    anchor_id: str
    kind: str
    content: str
    evidence_json: Optional[list] = None
    position_index: int


class MarkdownBlockUpdate(BaseModel):
    """Update payload for a markdown block."""

    content: str


class DeckResponse(BaseModel):
    """Deck response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    chapter_id: Optional[UUID] = None
    name: str
    status: str
    created_at: datetime
    card_count: int = 0
    pending_review: int = 0


class DeckListResponse(BaseModel):
    """List response for decks."""

    decks: list[DeckResponse]


class DeckGenerationRequest(BaseModel):
    """Request payload for generating decks from markdown."""

    chapter_ids: list[UUID]
    max_cards: int = 0
    focus: Optional[dict] = None
    custom_instructions: Optional[str] = None


class JobCreate(BaseModel):
    """Payload for creating a job."""

    project_id: UUID
    document_id: Optional[UUID] = None
    deck_id: Optional[UUID] = None
    job_type: str = "markdown_build"


class JobResponse(BaseModel):
    """Job response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    document_id: Optional[UUID] = None
    deck_id: Optional[UUID] = None
    job_type: str
    status: str
    progress: int
    current_step: Optional[str] = None
    created_at: datetime
    finished_at: Optional[datetime] = None


class JobListResponse(BaseModel):
    """List response for jobs."""

    jobs: list[JobResponse]


class CardDraftResponse(BaseModel):
    """Card draft response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deck_id: UUID
    anchor_id: Optional[str] = None
    front: str
    back: str
    tags: list[str] = []
    confidence: float
    flags_json: Optional[list] = None
    evidence_json: Optional[list] = None
    status: str


class CardDraftUpdate(BaseModel):
    """Update payload for card drafts."""

    front: Optional[str] = None
    back: Optional[str] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None


class CardDraftListResponse(BaseModel):
    """List response for card drafts."""

    cards: list[CardDraftResponse]


class CardRevisionResponse(BaseModel):
    """Card revision response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    card_id: UUID
    revision_number: int
    front: str
    back: str
    tags: list[str] = []
    edited_by: Optional[str] = None
    created_at: datetime


class CardRevisionListResponse(BaseModel):
    """List response for card revisions."""

    revisions: list[CardRevisionResponse]


class SlideResponse(BaseModel):
    """Slide response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    page_index: int
    image_object_key: str
    image_url: Optional[str] = None


class SlideListResponse(BaseModel):
    """List response for slides."""

    slides: list[SlideResponse]


class ExportRequest(BaseModel):
    """Request payload for exporting a deck."""

    format: str
    include_rejected: bool = False


class ExportResponse(BaseModel):
    """Export response payload."""

    export_id: UUID
    deck_id: UUID
    format: str
    download_url: str
    card_count: int


class ExportListResponse(BaseModel):
    """List response for exports."""

    exports: list[ExportResponse]
