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


class MarkdownPipelineState(TypedDict, total=False):
    """State passed through the markdown pipeline."""

    pdf_path: str
    pdf_data: bytes
    document: Document
    slides: list[Slide]
    claims: Annotated[list[Claim], _merge_claims]
    markdown_blocks: list[MarkdownBlock]
    markdown_content: str
    current_step: str
    progress: int
    errors: list[str]


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
