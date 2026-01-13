"""LangGraph pipeline components.

This module exports the pipeline builders for document processing:

Holistic Pipeline (Recommended):
    - build_holistic_graph: Process entire documents as coherent units
    - Produces higher quality markdown with natural deduplication
    - Smart image handling (formulas, diagrams, charts)
    - Chapter-based organization

Legacy Pipeline:
    - build_markdown_graph: Per-slide claim extraction
    - build_card_graph: Card generation from claims
    - build_slide_graph: Per-slide processing
    - build_region_graph: Per-region processing
"""

from slide2anki_core.graph.build_card_graph import build_card_graph
from slide2anki_core.graph.build_graph import build_graph
from slide2anki_core.graph.build_holistic_graph import (
    HolisticPipelineState,
    build_holistic_graph,
    build_holistic_graph_optimized,
)
from slide2anki_core.graph.build_markdown_graph import build_markdown_graph
from slide2anki_core.graph.build_region_graph import build_region_graph
from slide2anki_core.graph.build_slide_graph import build_slide_graph
from slide2anki_core.graph.config import GraphConfig, HolisticConfig

__all__ = [
    # Configuration
    "GraphConfig",
    "HolisticConfig",
    # Holistic pipeline (recommended)
    "build_holistic_graph",
    "build_holistic_graph_optimized",
    "HolisticPipelineState",
    # Legacy pipelines
    "build_graph",
    "build_markdown_graph",
    "build_card_graph",
    "build_region_graph",
    "build_slide_graph",
]
