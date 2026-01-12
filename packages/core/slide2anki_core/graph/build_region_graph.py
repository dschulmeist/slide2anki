"""Build the region-level extraction graph."""

from typing import TypedDict

from langgraph.graph import END, StateGraph

from slide2anki_core.graph.nodes import extract_region, repair_claims, verify_claims
from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.claims import Claim
from slide2anki_core.schemas.document import Slide
from slide2anki_core.schemas.regions import SlideRegion


class RegionPipelineState(TypedDict, total=False):
    """State passed through the region extraction pipeline."""

    slide: Slide
    region: SlideRegion
    claims: list[Claim]
    attempt: int
    max_attempts: int
    needs_repair: bool
    failed_claims: list[int]
    repair_suggestions: dict[int, str]
    current_step: str
    errors: list[str]


def _should_repair(state: RegionPipelineState) -> str:
    """Route to repair when verification fails and retries remain."""
    needs_repair = bool(state.get("needs_repair"))
    attempt = state.get("attempt", 0)
    max_attempts = state.get("max_attempts", 0)
    if needs_repair and attempt < max_attempts:
        return "repair_claims"
    return END


def build_region_graph(adapter: BaseModelAdapter) -> StateGraph:
    """Build a region-level extraction graph with verification loop.

    Args:
        adapter: Model adapter for vision calls

    Returns:
        Compiled StateGraph ready for invocation
    """
    graph = StateGraph(RegionPipelineState)

    graph.add_node("extract_region", extract_region.create_extract_region_node(adapter))
    graph.add_node("verify_claims", verify_claims.create_verify_claims_node(adapter))
    graph.add_node("repair_claims", repair_claims.create_repair_claims_node(adapter))

    graph.set_entry_point("extract_region")
    graph.add_edge("extract_region", "verify_claims")
    graph.add_conditional_edges("verify_claims", _should_repair)
    graph.add_edge("repair_claims", "verify_claims")

    return graph.compile()
