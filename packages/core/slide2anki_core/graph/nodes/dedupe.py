"""Dedupe node: Remove duplicate and overlapping cards."""

from typing import Any

from slide2anki_core.schemas.cards import CardDraft, CardFlag


def dedupe_node(state: dict[str, Any]) -> dict[str, Any]:
    """Remove duplicate and similar cards.

    Args:
        state: Pipeline state with cards

    Returns:
        Updated state with deduplicated cards
    """
    cards: list[CardDraft] = state.get("cards", [])
    if not cards:
        return {
            **state,
            "current_step": "dedupe",
            "progress": 90,
        }

    # Simple deduplication based on normalized text
    seen_fronts: set[str] = set()
    seen_backs: set[str] = set()
    unique_cards: list[CardDraft] = []

    for card in cards:
        # Normalize for comparison
        front_normalized = card.front.lower().strip()
        back_normalized = card.back.lower().strip()

        # Check for exact duplicates
        if front_normalized in seen_fronts:
            card.flags.append(CardFlag.DUPLICATE)
            continue

        # Check for very similar fronts (could be improved with fuzzy matching)
        is_similar = False
        for seen in seen_fronts:
            if _similarity(front_normalized, seen) > 0.85:
                is_similar = True
                card.flags.append(CardFlag.DUPLICATE)
                break

        if not is_similar:
            seen_fronts.add(front_normalized)
            seen_backs.add(back_normalized)
            unique_cards.append(card)

    return {
        **state,
        "cards": unique_cards,
        "current_step": "dedupe",
        "progress": 90,
    }


def _similarity(a: str, b: str) -> float:
    """Calculate simple similarity between two strings.

    Uses Jaccard similarity on word sets.
    """
    words_a = set(a.split())
    words_b = set(b.split())

    if not words_a or not words_b:
        return 0.0

    intersection = len(words_a & words_b)
    union = len(words_a | words_b)

    return intersection / union if union > 0 else 0.0
