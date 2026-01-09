"""APKG export for Anki decks."""

import hashlib
import random
from pathlib import Path
from typing import Optional, Union

from slide2anki_core.schemas.cards import CardDraft, CardStatus


def export_apkg(
    cards: list[CardDraft],
    deck_name: str,
    output: Union[str, Path],
    only_approved: bool = False,
    slide_images: Optional[dict[int, bytes]] = None,
) -> Path:
    """Export cards to APKG format (Anki deck package).

    Args:
        cards: List of card drafts
        deck_name: Name for the Anki deck
        output: Output file path
        only_approved: Only export approved cards
        slide_images: Optional dict mapping slide index to image bytes

    Returns:
        Path to the created APKG file
    """
    import genanki

    # Filter cards if needed
    if only_approved:
        cards = [c for c in cards if c.status == CardStatus.APPROVED]

    # Generate deterministic IDs based on deck name
    deck_id = _generate_id(deck_name)
    model_id = _generate_id(f"{deck_name}_model")

    # Create a basic model
    model = genanki.Model(
        model_id,
        f"{deck_name} Model",
        fields=[
            {"name": "Front"},
            {"name": "Back"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "{{Front}}",
                "afmt": '{{FrontSide}}<hr id="answer">{{Back}}',
            },
        ],
        css="""
        .card {
            font-family: arial;
            font-size: 20px;
            text-align: center;
            color: black;
            background-color: white;
        }
        """,
    )

    # Create deck
    deck = genanki.Deck(deck_id, deck_name)

    # Add cards
    media_files: list[str] = []
    for card in cards:
        note = genanki.Note(
            model=model,
            fields=[card.front, card.back],
            tags=card.tags,
        )
        deck.add_note(note)

    # Create package
    output_path = Path(output)
    package = genanki.Package(deck)
    package.media_files = media_files
    package.write_to_file(str(output_path))

    return output_path


def _generate_id(name: str) -> int:
    """Generate a deterministic ID from a string."""
    # Use hash to generate a consistent ID
    hash_bytes = hashlib.md5(name.encode()).digest()
    # Take first 8 bytes and convert to int, mask to 32 bits
    return int.from_bytes(hash_bytes[:4], "big") & 0x7FFFFFFF
