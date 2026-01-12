"""Build the main processing graph."""

from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.types import Send

from slide2anki_core.graph.build_slide_graph import build_slide_graph
from slide2anki_core.graph.config import GraphConfig
from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim
from slide2anki_core.schemas.document import Document, Slide
from slide2anki_core.utils.logging import get_logger

logger = get_logger(__name__)


def _merge_claims(existing: list[Claim], incoming: list[Claim]) -> list[Claim]:
    """Combine claim lists for reducer aggregation."""
    if not existing:
        return list(incoming or [])
    if not incoming:
        return list(existing)
    return [*existing, *incoming]


class PipelineState(TypedDict, total=False):
    """State passed through the pipeline."""

    # Input
    pdf_path: str
    pdf_data: bytes
    deck_name: str

    # Processing state
    document: Document
    slides: list[Slide]
    claims: Annotated[list[Claim], _merge_claims]
    cards: list[CardDraft]

    # Output
    export_path: str

    # Metadata
    current_step: str
    progress: int
    errors: list[str]

    # Config
    use_region_extraction: bool
    max_attempts: int


def build_graph(
    adapter: BaseModelAdapter,
    config: GraphConfig | None = None,
    use_region_extraction: bool = True,
) -> StateGraph:
    """Build the processing pipeline graph.

    Args:
        adapter: Model adapter for LLM calls
        config: Optional graph configuration
        use_region_extraction: If True, use slide/region-aware extraction with
            segmentation and verification. If False, use simple per-slide extraction.
            Default is True for better quality.

    Returns:
        Compiled StateGraph ready for invocation
    """
    from slide2anki_core.graph.nodes import (
        critique,
        dedupe,
        export,
        extract,
        ingest,
        render,
        write_cards,
    )

    resolved_config = config or GraphConfig()
    logger.info(
        f"Building pipeline (region_extraction={use_region_extraction}, "
        f"max_claim_repairs={resolved_config.max_claim_repairs}, "
        f"max_card_repairs={resolved_config.max_card_repairs})"
    )

    # Create the graph
    graph = StateGraph(PipelineState)

    # Add common nodes
    graph.add_node("ingest", ingest.ingest_node)
    graph.add_node("render", render.create_render_node())
    graph.add_node("write_cards", write_cards.create_write_cards_node(adapter))
    graph.add_node("critique", critique.create_critique_node(adapter))
    graph.add_node("dedupe", dedupe.dedupe_node)
    graph.add_node("export", export.export_node)

    if use_region_extraction:
        # Use the sophisticated slide-level graph with region segmentation
        slide_graph = build_slide_graph(adapter, resolved_config)

        def _dispatch_slides(state: PipelineState) -> list[Send]:
            """Dispatch each slide to the slide worker graph."""
            slides = state.get("slides", [])
            if not slides:
                logger.warning("No slides to dispatch for region extraction")
                return []

            logger.info(f"Dispatching {len(slides)} slides for region-aware extraction")
            return [
                Send(
                    "slide_worker",
                    {
                        "slide": slide,
                        "max_attempts": resolved_config.max_claim_repairs,
                    },
                )
                for slide in slides
            ]

        def _collect_claims(state: PipelineState) -> dict[str, Any]:
            """Collect claims after all slide workers complete."""
            claims = state.get("claims", [])
            logger.info(f"Collected {len(claims)} claims from region extraction")
            return {
                **state,
                "current_step": "extract",
                "progress": 50,
            }

        graph.add_node("slide_worker", slide_graph)
        graph.add_node("collect_claims", _collect_claims)

        # Define edges for region-aware extraction
        graph.set_entry_point("ingest")
        graph.add_edge("ingest", "render")
        graph.add_conditional_edges("render", _dispatch_slides)
        graph.add_edge("slide_worker", "collect_claims")
        graph.add_edge("collect_claims", "write_cards")
    else:
        # Use simple per-slide extraction (faster but less accurate)
        graph.add_node("extract", extract.create_extract_node(adapter))

        # Define edges for simple extraction
        graph.set_entry_point("ingest")
        graph.add_edge("ingest", "render")
        graph.add_edge("render", "extract")
        graph.add_edge("extract", "write_cards")

    # Common edges after extraction
    graph.add_edge("write_cards", "critique")
    graph.add_edge("critique", "dedupe")
    graph.add_edge("dedupe", "export")
    graph.add_edge("export", END)

    return graph.compile()


# Convenience function for backward compatibility
def build_simple_graph(adapter: BaseModelAdapter) -> StateGraph:
    """Build a simple pipeline without region-aware extraction.

    This is faster but may produce lower quality results for complex slides.

    Args:
        adapter: Model adapter for LLM calls

    Returns:
        Compiled StateGraph ready for invocation
    """
    return build_graph(adapter, use_region_extraction=False)
