"""Build the main processing graph."""

from typing import Any, TypedDict

from langgraph.graph import StateGraph, END

from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim
from slide2anki_core.schemas.document import Document, Slide


class PipelineState(TypedDict, total=False):
    """State passed through the pipeline."""

    # Input
    pdf_path: str
    pdf_data: bytes
    deck_name: str

    # Processing state
    document: Document
    slides: list[Slide]
    claims: list[Claim]
    cards: list[CardDraft]

    # Output
    export_path: str

    # Metadata
    current_step: str
    progress: int
    errors: list[str]


def build_graph(adapter: BaseModelAdapter) -> StateGraph:
    """Build the processing pipeline graph.

    Args:
        adapter: Model adapter for LLM calls

    Returns:
        Compiled StateGraph ready for invocation
    """
    from slide2anki_core.graph.nodes import (
        ingest,
        render,
        extract,
        write_cards,
        critique,
        dedupe,
        export,
    )

    # Create the graph
    graph = StateGraph(PipelineState)

    # Add nodes
    graph.add_node("ingest", ingest.ingest_node)
    graph.add_node("render", render.create_render_node())
    graph.add_node("extract", extract.create_extract_node(adapter))
    graph.add_node("write_cards", write_cards.create_write_cards_node(adapter))
    graph.add_node("critique", critique.create_critique_node(adapter))
    graph.add_node("dedupe", dedupe.dedupe_node)
    graph.add_node("export", export.export_node)

    # Define edges
    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "render")
    graph.add_edge("render", "extract")
    graph.add_edge("extract", "write_cards")
    graph.add_edge("write_cards", "critique")
    graph.add_edge("critique", "dedupe")
    graph.add_edge("dedupe", "export")
    graph.add_edge("export", END)

    return graph.compile()
