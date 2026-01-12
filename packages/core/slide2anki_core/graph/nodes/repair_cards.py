"""Repair node: Fix flashcards that failed critique."""

from collections.abc import Callable
from typing import Any

from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.cards import CardDraft

REPAIR_CARDS_PROMPT = """Rewrite the following flashcards to address the critique.

Rules:
- Keep each card atomic and concise.
- Preserve the meaning from the evidence.
- Return empty strings for cards that should be dropped.

Cards:
{cards}

Output format:
{{
  "repairs": [
    {{"index": 0, "front": "Updated front", "back": "Updated back"}}
  ]
}}
"""


def _format_cards(cards: list[CardDraft], indices: list[int]) -> str:
    """Format selected cards for repair prompt."""
    lines: list[str] = []
    for index in indices:
        card = cards[index]
        critique = card.critique or "No critique provided."
        lines.append(
            f"{index}. Q: {card.front}\n   A: {card.back}\n   Critique: {critique}"
        )
    return "\n".join(lines)


def _needs_repair(card: CardDraft) -> bool:
    """Return True when a card should be repaired."""
    return bool(card.flags) or bool(card.critique)


def create_repair_cards_node(
    adapter: BaseModelAdapter,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create a repair node that rewrites critiqued cards.

    Args:
        adapter: Model adapter for text calls

    Returns:
        Node function
    """

    async def repair_cards_node(state: dict[str, Any]) -> dict[str, Any]:
        """Repair critiqued cards using model suggestions.

        Args:
            state: Pipeline state with cards and critiques

        Returns:
            Updated state with repaired cards
        """
        cards: list[CardDraft] = state.get("cards", [])
        if not cards:
            return {
                **state,
                "current_step": "repair_cards",
                "repair_attempts": state.get("repair_attempts", 0),
            }

        indices = [i for i, card in enumerate(cards) if _needs_repair(card)]
        if not indices:
            return {
                **state,
                "current_step": "repair_cards",
                "repair_attempts": state.get("repair_attempts", 0),
            }

        prompt = REPAIR_CARDS_PROMPT.format(cards=_format_cards(cards, indices))
        data = await adapter.generate_structured(prompt=prompt, image_data=None)
        repairs = []
        if isinstance(data, dict):
            repairs = data.get("repairs", [])
        elif isinstance(data, list):
            repairs = data

        repair_map: dict[int, dict[str, str]] = {}
        for item in repairs:
            index = item.get("index")
            front = item.get("front")
            back = item.get("back")
            if (
                isinstance(index, int)
                and isinstance(front, str)
                and isinstance(back, str)
            ):
                repair_map[index] = {
                    "front": front.strip(),
                    "back": back.strip(),
                }

        for index in indices:
            repair = repair_map.get(index)
            if not repair:
                continue
            if repair["front"] and repair["back"]:
                cards[index].front = repair["front"]
                cards[index].back = repair["back"]
                cards[index].flags = []
                cards[index].critique = None

        attempts = state.get("repair_attempts", 0) + 1

        return {
            **state,
            "cards": cards,
            "repair_attempts": attempts,
            "current_step": "repair_cards",
        }

    return repair_cards_node
