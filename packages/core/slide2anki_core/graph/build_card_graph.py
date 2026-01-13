"""Build the card generation graph from markdown claims."""

from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.types import Checkpointer

from slide2anki_core.graph.config import GraphConfig
from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim


def _keep_last_str(existing: str | None, incoming: str | None) -> str | None:
    """Keep the latest value for progress tracking fields."""
    return incoming if incoming else existing


def _keep_max_int(existing: int, incoming: int) -> int:
    """Keep the maximum value for progress fields."""
    return max(existing or 0, incoming or 0)


def _merge_errors(existing: list[str], incoming: list[str]) -> list[str]:
    """Combine error lists, deduplicating."""
    if not existing:
        return list(incoming or [])
    if not incoming:
        return list(existing)
    return list(dict.fromkeys([*existing, *incoming]))


class CardPipelineState(TypedDict, total=False):
    """State passed through the card generation pipeline."""

    claims: list[Claim]
    cards: list[CardDraft]
    current_step: Annotated[str, _keep_last_str]
    progress: Annotated[int, _keep_max_int]
    errors: Annotated[list[str], _merge_errors]
    max_cards: int
    focus: dict
    custom_instructions: str
    repair_attempts: int
    max_repair_attempts: int


def _needs_repair(state: CardPipelineState) -> str:
    """Route to repair when critiqued cards remain."""
    cards = state.get("cards", [])
    attempts = state.get("repair_attempts", 0)
    max_attempts = state.get("max_repair_attempts", 0)
    if attempts >= max_attempts:
        return "dedupe"

    if any(card.flags or card.critique for card in cards):
        return "repair_cards"
    return "dedupe"


def build_card_graph(
    adapter: BaseModelAdapter,
    config: GraphConfig | None = None,
    checkpointer: Checkpointer | None = None,
) -> StateGraph:
    """Build a pipeline that generates cards from claims.

    Args:
        adapter: Model adapter for LLM calls
        config: Optional graph configuration
        checkpointer: Optional LangGraph checkpointer

    Returns:
        Compiled StateGraph ready for invocation
    """
    from slide2anki_core.graph.nodes import (
        critique,
        dedupe,
        export,
        repair_cards,
        write_cards,
    )

    resolved_config = config or GraphConfig()

    graph = StateGraph(CardPipelineState)

    graph.add_node("write_cards", write_cards.create_write_cards_node(adapter))
    graph.add_node("critique", critique.create_critique_node(adapter))
    graph.add_node("repair_cards", repair_cards.create_repair_cards_node(adapter))
    graph.add_node("dedupe", dedupe.dedupe_node)
    graph.add_node("export", export.export_node)

    def _seed_repair_state(state: CardPipelineState) -> dict[str, int]:
        """Initialize repair counters for the card loop."""
        return {
            "repair_attempts": state.get("repair_attempts", 0),
            "max_repair_attempts": resolved_config.max_card_repairs,
        }

    graph.add_node("repair_seed", _seed_repair_state)

    graph.set_entry_point("write_cards")
    graph.add_edge("write_cards", "repair_seed")
    graph.add_edge("repair_seed", "critique")
    graph.add_conditional_edges("critique", _needs_repair)
    graph.add_edge("repair_cards", "critique")
    graph.add_edge("dedupe", "export")
    graph.add_edge("export", END)

    return graph.compile(checkpointer=checkpointer)
