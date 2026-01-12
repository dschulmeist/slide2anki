"""Build the markdown extraction graph."""

from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.types import Checkpointer, Send

from slide2anki_core.graph.build_slide_graph import build_slide_graph
from slide2anki_core.graph.config import GraphConfig
from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.claims import Claim
from slide2anki_core.schemas.document import Document, Slide
from slide2anki_core.schemas.markdown import MarkdownBlock


def _merge_claims(existing: list[Claim], incoming: list[Claim]) -> list[Claim]:
    """Combine claim lists for reducer aggregation."""
    if not existing:
        return list(incoming or [])
    if not incoming:
        return list(existing)
    return [*existing, *incoming]


def _merge_errors(existing: list[str], incoming: list[str]) -> list[str]:
    """Combine error lists from parallel workers, deduplicating."""
    if not existing:
        return list(incoming or [])
    if not incoming:
        return list(existing)
    # Use dict.fromkeys to preserve order while deduplicating
    return list(dict.fromkeys([*existing, *incoming]))


def _ignore_slide(existing: Slide | None, incoming: Slide | None) -> Slide | None:
    """Reducer that ignores incoming slide values from parallel workers.

    Each slide worker processes its own slide and returns it in state.
    We don't need to aggregate these at the parent level, so we just
    keep the existing value (or take the first one if none exists).
    """
    return existing if existing is not None else incoming


class MarkdownPipelineState(TypedDict, total=False):
    """State passed through the markdown pipeline."""

    pdf_path: str
    pdf_data: bytes
    document: Document
    slides: list[Slide]
    # slide: receives values from parallel slide_workers, ignored at parent level
    slide: Annotated[Slide | None, _ignore_slide]
    claims: Annotated[list[Claim], _merge_claims]
    markdown_blocks: list[MarkdownBlock]
    markdown_content: str
    current_step: str
    progress: int
    errors: Annotated[list[str], _merge_errors]


def _dispatch_slides(state: MarkdownPipelineState) -> list[Send]:
    """Send each slide into the slide worker subgraph."""
    slides = state.get("slides", [])
    if not slides:
        return []
    return [Send("slide_worker", {"slide": slide}) for slide in slides]


def build_markdown_graph(
    adapter: BaseModelAdapter,
    config: GraphConfig | None = None,
    checkpointer: Checkpointer | None = None,
) -> StateGraph:
    """Build a pipeline that extracts markdown blocks from a document.

    Args:
        adapter: Model adapter for vision calls
        config: Optional graph configuration
        checkpointer: Optional LangGraph checkpointer

    Returns:
        Compiled StateGraph ready for invocation
    """
    from slide2anki_core.graph.nodes import ingest, markdown, render

    resolved_config = config or GraphConfig()
    slide_graph = build_slide_graph(adapter, resolved_config)

    graph = StateGraph(MarkdownPipelineState)

    graph.add_node("ingest", ingest.ingest_node)
    graph.add_node("render", render.create_render_node())
    graph.add_node("slide_worker", slide_graph)
    graph.add_node("markdown", markdown.create_markdown_node())

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "render")
    graph.add_conditional_edges("render", _dispatch_slides)
    graph.add_edge("slide_worker", "markdown")
    graph.add_edge("markdown", END)

    return graph.compile(checkpointer=checkpointer)
