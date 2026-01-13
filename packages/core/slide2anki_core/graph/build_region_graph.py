"""Build the region-level extraction graph."""

from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph

from slide2anki_core.graph.nodes import extract_region, repair_claims, verify_claims
from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.claims import Claim
from slide2anki_core.schemas.document import Slide
from slide2anki_core.schemas.regions import SlideRegion
from slide2anki_core.utils.logging import get_logger

logger = get_logger(__name__)


def _keep_last_str(existing: str | None, incoming: str | None) -> str | None:
    """Keep the latest value for progress tracking fields."""
    return incoming if incoming else existing


def _merge_errors(existing: list[str], incoming: list[str]) -> list[str]:
    """Combine error lists, deduplicating."""
    if not existing:
        return list(incoming or [])
    if not incoming:
        return list(existing)
    return list(dict.fromkeys([*existing, *incoming]))


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
    skip_verification: bool  # Skip verify/repair for text-only or fast mode
    current_step: Annotated[str, _keep_last_str]
    errors: Annotated[list[str], _merge_errors]


def _should_verify(state: RegionPipelineState) -> str:
    """Route to verify or skip directly to end for fast mode or text-only slides."""
    # Fast mode: skip verification entirely
    if state.get("skip_verification"):
        logger.info("Skipping verification (fast_mode enabled)")
        return END
    # Skip verification for text-only slides - text extraction is reliable
    slide = state.get("slide")
    if slide and getattr(slide, "is_text_only", False):
        logger.info(f"Skipping verification for text-only slide {slide.page_index}")
        return END
    return "verify_claims"


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
    # Route to verify or skip based on slide type
    graph.add_conditional_edges("extract_region", _should_verify)
    graph.add_conditional_edges("verify_claims", _should_repair)
    graph.add_edge("repair_claims", "verify_claims")

    return graph.compile()
