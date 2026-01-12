"""Build the slide-level extraction graph."""

from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.types import Send

from slide2anki_core.graph.build_region_graph import build_region_graph
from slide2anki_core.graph.config import GraphConfig
from slide2anki_core.graph.nodes import segment
from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.claims import Claim
from slide2anki_core.schemas.document import Slide
from slide2anki_core.schemas.regions import SlideRegion


def _merge_claims(existing: list[Claim], incoming: list[Claim]) -> list[Claim]:
    """Combine claim lists for reducer aggregation."""
    if not existing:
        return list(incoming or [])
    if not incoming:
        return list(existing)
    return [*existing, *incoming]


class SlidePipelineState(TypedDict, total=False):
    """State passed through the slide extraction pipeline."""

    slide: Slide
    regions: list[SlideRegion]
    claims: Annotated[list[Claim], _merge_claims]
    max_attempts: int
    current_step: str
    errors: list[str]


def _dispatch_regions(state: SlidePipelineState) -> list[Send]:
    """Dispatch each region to the region worker graph."""
    regions = state.get("regions", [])
    slide = state.get("slide")
    if not slide:
        return []
    max_attempts = state.get("max_attempts", 0)
    return [
        Send(
            "region_worker",
            {
                "slide": slide,
                "region": region,
                "attempt": 0,
                "max_attempts": max_attempts,
            },
        )
        for region in regions
    ]


def build_slide_graph(
    adapter: BaseModelAdapter,
    config: GraphConfig | None = None,
) -> StateGraph:
    """Build a slide-level graph that segments and extracts claims.

    Args:
        adapter: Model adapter for vision calls
        config: Optional graph configuration

    Returns:
        Compiled StateGraph ready for invocation
    """
    resolved_config = config or GraphConfig()
    region_graph = build_region_graph(adapter)

    graph = StateGraph(SlidePipelineState)

    graph.add_node("segment", segment.create_segment_node(adapter))
    graph.add_node("region_worker", region_graph)
    graph.add_conditional_edges("segment", _dispatch_regions)
    graph.add_edge("region_worker", END)

    def _inject_config(state: SlidePipelineState) -> dict[str, Any]:
        """Inject configuration values into the slide state."""
        return {
            **state,
            "max_attempts": resolved_config.max_claim_repairs,
        }

    graph.add_node("config", _inject_config)
    graph.add_edge("config", "segment")
    graph.set_entry_point("config")

    return graph.compile()
