"""Build the markdown extraction graph."""

from typing import TypedDict

from langgraph.graph import END, StateGraph

from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.document import Document, Slide
from slide2anki_core.schemas.markdown import MarkdownBlock


class MarkdownPipelineState(TypedDict, total=False):
    """State passed through the markdown pipeline."""

    pdf_path: str
    pdf_data: bytes
    document: Document
    slides: list[Slide]
    markdown_blocks: list[MarkdownBlock]
    markdown_content: str
    current_step: str
    progress: int
    errors: list[str]


def build_markdown_graph(adapter: BaseModelAdapter) -> StateGraph:
    """Build a pipeline that extracts markdown blocks from a document.

    Args:
        adapter: Model adapter for vision calls

    Returns:
        Compiled StateGraph ready for invocation
    """
    from slide2anki_core.graph.nodes import extract, ingest, markdown, render

    graph = StateGraph(MarkdownPipelineState)

    graph.add_node("ingest", ingest.ingest_node)
    graph.add_node("render", render.create_render_node())
    graph.add_node("extract", extract.create_extract_node(adapter))
    graph.add_node("markdown", markdown.create_markdown_node())

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "render")
    graph.add_edge("render", "extract")
    graph.add_edge("extract", "markdown")
    graph.add_edge("markdown", END)

    return graph.compile()
