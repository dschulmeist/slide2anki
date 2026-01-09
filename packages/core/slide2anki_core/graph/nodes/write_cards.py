"""Write cards node: Generate flashcard drafts from claims."""

from typing import Any, Callable

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
        claims_text = "\n".join(
            f"- [{c.kind.value}] {c.statement}" for c in claims
        )
        prompt = WRITE_CARDS_PROMPT.format(claims=claims_text)

        try:
            # Call LLM
            response = await adapter.generate_cards(
                claims=claims,
                prompt=prompt,
            )

            # Create card drafts
            cards = []
            claim_map = {c.statement: c for c in claims}

            for card_data in response:
                # Try to find matching claim for evidence
                evidence = []
                for claim in claims:
                    if claim.statement in card_data.get("front", "") or \
                       claim.statement in card_data.get("back", ""):
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
