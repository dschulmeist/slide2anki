"""Export node: Generate output files."""

from typing import Any

from slide2anki_core.schemas.cards import CardDraft, CardStatus


def export_node(state: dict[str, Any]) -> dict[str, Any]:
    """Prepare cards for export.

    Note: Actual file generation is handled by exporters module.
    This node filters and prepares the final card list.

    Args:
        state: Pipeline state with cards

    Returns:
        Updated state with export-ready cards
    """
    cards: list[CardDraft] = state.get("cards", [])

    # Filter to approved or pending cards (exclude rejected)
    export_cards = [
        c for c in cards
        if c.status in (CardStatus.PENDING, CardStatus.APPROVED)
    ]

    return {
        **state,
        "cards": export_cards,
        "current_step": "export",
        "progress": 100,
    }
