"""Pydantic schemas for API request and response models."""

from datetime import datetime
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
    created_by: str | None = None


class MarkdownBlockResponse(BaseModel):
    """Markdown block response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    chapter_id: UUID
    anchor_id: str
    kind: str
    content: str
    evidence_json: list | None = None
    position_index: int


class MarkdownBlockUpdate(BaseModel):
    """Update payload for a markdown block."""

    content: str


class DeckResponse(BaseModel):
    """Deck response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    chapter_id: UUID | None = None
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
    focus: dict | None = None
    custom_instructions: str | None = None


class JobCreate(BaseModel):
    """Payload for creating a job."""

    project_id: UUID
    document_id: UUID | None = None
    deck_id: UUID | None = None
    job_type: str = "markdown_build"


class JobResponse(BaseModel):
    """Job response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    document_id: UUID | None = None
    deck_id: UUID | None = None
    job_type: str
    status: str
    progress: int
    current_step: str | None = None
    error_message: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class JobListResponse(BaseModel):
    """List response for jobs."""

    jobs: list[JobResponse]


class CardDraftResponse(BaseModel):
    """Card draft response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deck_id: UUID
    anchor_id: str | None = None
    front: str
    back: str
    tags: list[str] = []
    confidence: float
    flags_json: list | None = None
    evidence_json: list | None = None
    status: str


class CardDraftUpdate(BaseModel):
    """Update payload for card drafts."""

    front: str | None = None
    back: str | None = None
    tags: list[str] | None = None
    status: str | None = None


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
    edited_by: str | None = None


class JobEventResponse(BaseModel):
    """Job event response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    level: str
    message: str
    step: str | None = None
    progress: int | None = None
    details_json: dict | None = None
    created_at: datetime


class JobEventListResponse(BaseModel):
    """List response for job events."""

    events: list[JobEventResponse]


class AppSettingsResponse(BaseModel):
    """Response payload for application settings (masked)."""

    model_config = ConfigDict(from_attributes=True)

    provider: str
    model: str
    base_url: str | None = None
    api_key_present: bool = False
    updated_at: datetime


class AppSettingsUpdate(BaseModel):
    """Update payload for application settings.

    Notes:
        - api_key is write-only; the API never returns the raw secret.
        - api_key may be omitted to keep the existing key.
    """

    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None


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
    image_url: str | None = None


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
