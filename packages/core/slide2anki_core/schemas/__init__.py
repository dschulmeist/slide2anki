"""Data schemas for the pipeline."""

from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim, Evidence
from slide2anki_core.schemas.document import Document, Slide

__all__ = [
    "CardDraft",
    "Claim",
    "Document",
    "Evidence",
    "Slide",
]
