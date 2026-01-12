"""Write cards node: Generate flashcard drafts from claims."""

from collections.abc import Callable
from typing import Any

from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim

WRITE_CARDS_PROMPT = """Convert these claims into Anki flashcards.

Rules:
1. One fact per card - atomic, focused questions
2. Minimal wording - be concise
3. No "hint" words that give away the answer
4. Answer should be short and specific
5. Include relevant tags

Claims:
{claims}

Output format (JSON array):
[
  {{
    "front": "What is the primary function of mitochondria?",
    "back": "Produce ATP through cellular respiration",
    "tags": ["biology", "cell-organelles"],
    "confidence": 0.9
  }},
  ...
]
"""


def _build_prompt(
    claims_text: str,
    max_cards: int | None,
    focus: dict | None,
    custom_instructions: str | None,
) -> str:
    """Build a prompt that includes optional generation constraints.

    Args:
        claims_text: Formatted claims text
        max_cards: Optional maximum number of cards to generate
        focus: Optional focus configuration dictionary
        custom_instructions: Optional free-form instruction string

    Returns:
        Prompt string for card generation
    """
    instructions = []
    if max_cards and max_cards > 0:
        instructions.append(f"- Generate at most {max_cards} cards.")
    if focus:
        focus_items: list[str] = []
        if isinstance(focus, dict):
            focus_items = [str(key).strip() for key, value in focus.items() if value]
        elif isinstance(focus, (list, tuple, set)):
            focus_items = [str(item).strip() for item in focus]
        else:
            focus_items = [str(focus).strip()]

        focus_items = sorted({item for item in focus_items if item})
        if focus_items:
            instructions.append(f"- Emphasize: {', '.join(focus_items)}.")
    if custom_instructions:
        instructions.append(f"- {custom_instructions.strip()}")

    extra = "\n".join(instructions)
    if extra:
        extra = f"\nAdditional instructions:\n{extra}\n"

    return WRITE_CARDS_PROMPT.format(claims=claims_text) + extra


def create_write_cards_node(
    adapter: BaseModelAdapter,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create a write cards node with the given model adapter.

    Args:
        adapter: Model adapter for LLM calls

    Returns:
        Node function
    """

    async def write_cards_node(state: dict[str, Any]) -> dict[str, Any]:
        """Generate flashcard drafts from claims.

        Args:
            state: Pipeline state with claims

        Returns:
            Updated state with card drafts
        """
        claims: list[Claim] = state.get("claims", [])
        if not claims:
            return {
                **state,
                "cards": [],
                "current_step": "write_cards",
                "progress": 65,
            }

        # Format claims for prompt
        claims_text = "\n".join(f"- [{c.kind.value}] {c.statement}" for c in claims)
        prompt = _build_prompt(
            claims_text=claims_text,
            max_cards=state.get("max_cards"),
            focus=state.get("focus"),
            custom_instructions=state.get("custom_instructions"),
        )

        try:
            # Call LLM
            response = await adapter.generate_cards(
                claims=claims,
                prompt=prompt,
            )

            # Create card drafts
            cards = []

            for card_data in response:
                # Try to find matching claim for evidence
                evidence = []
                for claim in claims:
                    if claim.statement in card_data.get(
                        "front", ""
                    ) or claim.statement in card_data.get("back", ""):
                        evidence.append(claim.evidence)
                        break

                card = CardDraft(
                    front=card_data["front"],
                    back=card_data["back"],
                    tags=card_data.get("tags", []),
                    confidence=card_data.get("confidence", 1.0),
                    evidence=evidence,
                )
                cards.append(card)

            return {
                **state,
                "cards": cards,
                "current_step": "write_cards",
                "progress": 65,
            }

        except Exception as e:
            return {
                **state,
                "errors": state.get("errors", []) + [f"Write cards error: {str(e)}"],
                "cards": [],
                "current_step": "write_cards",
            }

    return write_cards_node
