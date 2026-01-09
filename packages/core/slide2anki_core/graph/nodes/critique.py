"""Critique node: Evaluate and improve card quality."""

from typing import Any, Callable

from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.cards import CardDraft, CardFlag

CRITIQUE_PROMPT = """Review these flashcard drafts and identify issues.

For each card, check for:
1. Ambiguity - Is the question clear? Could it have multiple answers?
2. Length - Is it too long or verbose?
3. Context - Does it need more context to make sense?
4. Quality - Is it a good learning card?

Cards:
{cards}

Output format (JSON array):
[
  {{
    "index": 0,
    "flags": ["ambiguous", "too_long"],
    "critique": "The question could refer to multiple processes. Consider being more specific.",
    "suggested_front": "What is the primary function of mitochondria in eukaryotic cells?",
    "suggested_back": "ATP production via cellular respiration"
  }},
  ...
]

Only include cards that need improvement. Use flags:
- ambiguous: Question is unclear
- too_long: Content is verbose
- missing_context: Needs more context
- low_confidence: Uncertain about accuracy
"""


def create_critique_node(
    adapter: BaseModelAdapter,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create a critique node with the given model adapter.

    Args:
        adapter: Model adapter for LLM calls

    Returns:
        Node function
    """

    async def critique_node(state: dict[str, Any]) -> dict[str, Any]:
        """Critique and improve card drafts.

        Args:
            state: Pipeline state with cards

        Returns:
            Updated state with critiqued cards
        """
        cards: list[CardDraft] = state.get("cards", [])
        if not cards:
            return {
                **state,
                "current_step": "critique",
                "progress": 80,
            }

        # Format cards for prompt
        cards_text = "\n".join(
            f"{i}. Q: {c.front}\n   A: {c.back}"
            for i, c in enumerate(cards)
        )
        prompt = CRITIQUE_PROMPT.format(cards=cards_text)

        try:
            # Call LLM
            critiques = await adapter.critique_cards(
                cards=cards,
                prompt=prompt,
            )

            # Apply critiques to cards
            critique_map = {c["index"]: c for c in critiques}

            updated_cards = []
            for i, card in enumerate(cards):
                if i in critique_map:
                    critique_data = critique_map[i]

                    # Add flags
                    flags = [
                        CardFlag(f) for f in critique_data.get("flags", [])
                        if f in [e.value for e in CardFlag]
                    ]
                    card.flags = flags
                    card.critique = critique_data.get("critique")

                    # Apply suggestions if provided
                    if critique_data.get("suggested_front"):
                        card.front = critique_data["suggested_front"]
                    if critique_data.get("suggested_back"):
                        card.back = critique_data["suggested_back"]

                updated_cards.append(card)

            return {
                **state,
                "cards": updated_cards,
                "current_step": "critique",
                "progress": 80,
            }

        except Exception as e:
            return {
                **state,
                "errors": state.get("errors", []) + [f"Critique error: {str(e)}"],
                "current_step": "critique",
            }

    return critique_node
