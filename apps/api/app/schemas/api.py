from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# Deck schemas
class DeckCreate(BaseModel):
    name: str


class DeckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: str
    created_at: datetime


class DeckListResponse(BaseModel):
    decks: list[DeckResponse]


# Upload schemas
class UploadResponse(BaseModel):
    upload_id: UUID
    deck_id: UUID
    filename: str
    object_key: str


# Job schemas
class JobCreate(BaseModel):
    deck_id: UUID


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deck_id: UUID
    status: str
    progress: int
    current_step: Optional[str] = None
    created_at: datetime
    finished_at: Optional[datetime] = None


class JobListResponse(BaseModel):
    jobs: list[JobResponse]


# Card schemas
class CardDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deck_id: UUID
    front: str
    back: str
    tags: list[str] = []
    confidence: float
    flags_json: Optional[dict] = None
    evidence_json: Optional[dict] = None
    status: str


class CardDraftUpdate(BaseModel):
    front: Optional[str] = None
    back: Optional[str] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None


class CardDraftListResponse(BaseModel):
    cards: list[CardDraftResponse]


# Slide schemas
class SlideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deck_id: UUID
    page_index: int
    image_object_key: str


class SlideListResponse(BaseModel):
    slides: list[SlideResponse]


# Export schemas
class ExportRequest(BaseModel):
    format: str  # "tsv" or "apkg"


class ExportResponse(BaseModel):
    export_id: UUID
    deck_id: UUID
    format: str
    download_url: str
    card_count: int


class ExportListResponse(BaseModel):
    exports: list[ExportResponse]
