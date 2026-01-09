"""slide2anki-core: Pipeline for converting slides to Anki flashcards."""

from slide2anki_core.graph.build_graph import build_graph
from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim
from slide2anki_core.schemas.document import Document, Slide

__version__ = "0.1.0"

__all__ = [
    "build_graph",
    "CardDraft",
    "Claim",
    "Document",
    "Slide",
]
