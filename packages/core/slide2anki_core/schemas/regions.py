"""Slide region schemas used for segmented extraction.

This module defines schemas for the legacy per-slide extraction pipeline
that segments slides into regions (title, bullets, equations, diagrams, etc.)
before extracting claims from each region.

Note: The holistic pipeline does not use region segmentation. It processes
entire documents as coherent units for better context and deduplication.
"""

from enum import Enum

from pydantic import BaseModel, Field

from slide2anki_core.schemas.claims import BoundingBox


class RegionKind(str, Enum):
    """Types of slide regions for segmentation."""

    TITLE = "title"
    BULLETS = "bullets"
    TABLE = "table"
    EQUATION = "equation"
    DIAGRAM = "diagram"
    IMAGE = "image"
    OTHER = "other"


class SlideRegion(BaseModel):
    """A segmented region within a slide."""

    kind: RegionKind = Field(..., description="Region classification")
    bbox: BoundingBox = Field(..., description="Region bounding box")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Model confidence")
    text_snippet: str | None = Field(
        None, description="Optional text snippet describing the region"
    )
