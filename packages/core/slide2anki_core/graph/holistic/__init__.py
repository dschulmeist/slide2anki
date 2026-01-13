"""Holistic document processing pipeline nodes.

This package contains nodes for the holistic document processing pipeline,
which processes entire documents as coherent units rather than extracting
claims per-slide. This approach produces higher quality markdown with:

- Natural deduplication (metadata mentioned once, not per-slide)
- Proper context (understands document flow and relationships)
- Smart image handling (transcribe formulas, describe diagrams)
- Chapter-based organization (logical structure, not slide order)

Pipeline flow:
    ingest -> render -> extract_images -> classify_images -> transcribe_images
                              |
                              v
                    extract_document (chunked)
                              |
                              v
                      detect_chapters
                              |
                              v
                    assemble_markdown
                              |
                              v
                      generate_cards
"""

from slide2anki_core.graph.holistic.assemble_markdown import (
    create_assemble_markdown_node,
)
from slide2anki_core.graph.holistic.classify_images import create_classify_images_node
from slide2anki_core.graph.holistic.detect_chapters import create_detect_chapters_node
from slide2anki_core.graph.holistic.extract_document import (
    create_extract_document_node,
)
from slide2anki_core.graph.holistic.extract_images import create_extract_images_node
from slide2anki_core.graph.holistic.transcribe_images import (
    create_transcribe_images_node,
)

__all__ = [
    "create_assemble_markdown_node",
    "create_classify_images_node",
    "create_detect_chapters_node",
    "create_extract_document_node",
    "create_extract_images_node",
    "create_transcribe_images_node",
]
