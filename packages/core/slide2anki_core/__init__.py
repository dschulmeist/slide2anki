"""slide2anki-core: Pipeline for converting slides to Anki flashcards.

This package provides document processing pipelines for extracting educational
content from PDF slides and generating Anki flashcards.

Two pipeline approaches are available:

Holistic Pipeline (Recommended):
    Processes entire documents as coherent units, producing higher quality
    markdown with natural deduplication and proper context.

    >>> from slide2anki_core.graph import build_holistic_graph, HolisticConfig
    >>> graph = build_holistic_graph(adapter, HolisticConfig())
    >>> result = await graph.ainvoke({"pdf_data": pdf_bytes})

Legacy Pipeline:
    Per-slide extraction with region segmentation. Kept for backward
    compatibility but may produce redundant or lower quality output.

    >>> from slide2anki_core.graph import build_markdown_graph
    >>> graph = build_markdown_graph(adapter)
    >>> result = await graph.ainvoke({"pdf_data": pdf_bytes})

For more details, see the `graph` subpackage documentation.
"""

from slide2anki_core.graph import (
    HolisticConfig,
    build_holistic_graph,
)
from slide2anki_core.graph.build_graph import build_graph
from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim
from slide2anki_core.schemas.document import Document, Slide

__version__ = "0.1.0"

__all__ = [
    # Holistic pipeline (recommended)
    "build_holistic_graph",
    "HolisticConfig",
    # Legacy pipeline
    "build_graph",
    # Schemas
    "CardDraft",
    "Claim",
    "Document",
    "Slide",
]
