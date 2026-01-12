"""Build the card generation graph from markdown claims."""

from typing import TypedDict

from langgraph.graph import END, StateGraph

from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim


class CardPipelineState(TypedDict, total=False):
    """State passed through the card generation pipeline."""

    claims: list[Claim]
    cards: list[CardDraft]
    current_step: str
    progress: int
    errors: list[str]
    max_cards: int
    focus: dict
    custom_instructions: str


def build_card_graph(adapter: BaseModelAdapter) -> StateGraph:
    """Build a pipeline that generates cards from claims.

    Args:
        adapter: Model adapter for LLM calls

    Returns:
        Compiled StateGraph ready for invocation
    """
    from slide2anki_core.graph.nodes import critique, dedupe, export, write_cards

    graph = StateGraph(CardPipelineState)

    graph.add_node("write_cards", write_cards.create_write_cards_node(adapter))
    graph.add_node("critique", critique.create_critique_node(adapter))
    graph.add_node("dedupe", dedupe.dedupe_node)
    graph.add_node("export", export.export_node)

    graph.set_entry_point("write_cards")
    graph.add_edge("write_cards", "critique")
    graph.add_edge("critique", "dedupe")
    graph.add_edge("dedupe", "export")
    graph.add_edge("export", END)

    return graph.compile()
