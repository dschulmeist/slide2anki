"""Data schemas for the pipeline.

This module exports all core data schemas used throughout the slide2anki
processing pipeline, including document models, claim extraction, image
processing, chapter organization, and flashcard generation.
"""

from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.chapters import (
    Chapter,
    ChapterOutline,
    ChunkingConfig,
    DocumentChunk,
)
from slide2anki_core.schemas.claims import Claim, Evidence
from slide2anki_core.schemas.document import Document, Slide
from slide2anki_core.schemas.images import (
    ExtractedImage,
    ImagePosition,
    ImageType,
    ProcessedImage,
)
from slide2anki_core.schemas.markdown import MarkdownBlock
from slide2anki_core.schemas.regions import RegionKind, SlideRegion

__all__ = [
    # Document and slides
    "Document",
    "Slide",
    # Claims and evidence
    "Claim",
    "Evidence",
    # Images
    "ExtractedImage",
    "ImagePosition",
    "ImageType",
    "ProcessedImage",
    # Chapters
    "Chapter",
    "ChapterOutline",
    "ChunkingConfig",
    "DocumentChunk",
    # Markdown
    "MarkdownBlock",
    # Cards
    "CardDraft",
    # Regions (legacy)
    "RegionKind",
    "SlideRegion",
]
