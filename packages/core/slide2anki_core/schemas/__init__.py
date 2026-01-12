"""Data schemas for the pipeline."""

from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim, Evidence
from slide2anki_core.schemas.document import Document, Slide
from slide2anki_core.schemas.markdown import MarkdownBlock
from slide2anki_core.schemas.regions import RegionKind, SlideRegion

__all__ = [
    "CardDraft",
    "Claim",
    "Document",
    "Evidence",
    "MarkdownBlock",
    "RegionKind",
    "Slide",
    "SlideRegion",
]
