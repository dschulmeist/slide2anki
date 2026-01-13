"""Pipeline nodes for the legacy per-slide extraction pipeline.

This module contains nodes for the legacy extraction approach that processes
documents slide-by-slide with region segmentation. For new projects, consider
using the holistic pipeline in `slide2anki_core.graph.holistic` instead.

Legacy Pipeline Nodes:
    - ingest: PDF validation and document creation
    - render: PDF to image conversion with text-only detection
    - segment: Layout segmentation into regions
    - extract_region: Per-region claim extraction
    - verify_claims: Claim verification loop
    - repair_claims: Claim repair from verification feedback
    - markdown: Claim deduplication and markdown block creation
    - write_cards: Card generation from claims
    - critique: Card quality assessment
    - repair_cards: Card repair from critique feedback
    - dedupe: Card deduplication
    - export: TSV/APKG export

Note: The `ingest` and `render` nodes are also used by the holistic pipeline.
"""

from slide2anki_core.graph.nodes import (
    critique,
    dedupe,
    export,
    extract,
    extract_region,
    ingest,
    markdown,
    render,
    repair_cards,
    repair_claims,
    segment,
    verify_claims,
    write_cards,
)

__all__ = [
    "critique",
    "dedupe",
    "export",
    "extract",
    "extract_region",
    "ingest",
    "markdown",
    "render",
    "repair_cards",
    "repair_claims",
    "segment",
    "verify_claims",
    "write_cards",
]
