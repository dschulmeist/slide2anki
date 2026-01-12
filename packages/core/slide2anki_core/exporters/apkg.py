"""APKG export for Anki decks."""

import hashlib
import tempfile
from io import BytesIO
from pathlib import Path

from slide2anki_core.evidence.crop import CropError, crop_evidence
from slide2anki_core.schemas.cards import CardDraft, CardStatus
from slide2anki_core.schemas.claims import Evidence
from slide2anki_core.utils.logging import get_logger

logger = get_logger(__name__)


def export_apkg(
    cards: list[CardDraft],
    deck_name: str,
    output: str | Path,
    only_approved: bool = False,
    slide_images: dict[int, bytes] | None = None,
    embed_evidence: bool = True,
) -> Path:
    """Export cards to APKG format (Anki deck package).

    Args:
        cards: List of card drafts
        deck_name: Name for the Anki deck
        output: Output file path
        only_approved: Only export approved cards
        slide_images: Optional dict mapping slide index to image bytes
        embed_evidence: Whether to embed evidence images in cards (requires slide_images)

    Returns:
        Path to the created APKG file
    """
    import genanki

    logger.info(f"Exporting APKG: {deck_name} ({len(cards)} cards, embed_evidence={embed_evidence})")

    # Filter cards if needed
    if only_approved:
        cards = [c for c in cards if c.status == CardStatus.APPROVED]
        logger.info(f"Filtered to {len(cards)} approved cards")

    # Generate deterministic IDs based on deck name
    deck_id = _generate_id(deck_name)
    model_id = _generate_id(f"{deck_name}_model")

    # Create model with or without evidence field
    if embed_evidence and slide_images:
        model = _create_model_with_evidence(model_id, deck_name)
    else:
        model = _create_basic_model(model_id, deck_name)

    # Create deck
    deck = genanki.Deck(deck_id, deck_name)

    # Track media files to embed
    media_files: list[str] = []
    temp_dir = tempfile.mkdtemp(prefix="anki_media_")

    # Add cards
    for i, card in enumerate(cards):
        try:
            if embed_evidence and slide_images and card.evidence:
                # Create card with embedded evidence image
                evidence_html, card_media = _create_evidence_html(
                    card.evidence,
                    slide_images,
                    temp_dir,
                    card_index=i,
                )
                media_files.extend(card_media)

                note = genanki.Note(
                    model=model,
                    fields=[card.front, card.back, evidence_html],
                    tags=card.tags,
                )
            else:
                # Basic card without evidence
                if embed_evidence and slide_images:
                    # Model expects 3 fields
                    note = genanki.Note(
                        model=model,
                        fields=[card.front, card.back, ""],
                        tags=card.tags,
                    )
                else:
                    note = genanki.Note(
                        model=model,
                        fields=[card.front, card.back],
                        tags=card.tags,
                    )
            deck.add_note(note)
        except Exception as e:
            logger.warning(f"Failed to create note for card {i}: {e}")
            # Fall back to basic note
            if embed_evidence and slide_images:
                note = genanki.Note(
                    model=model,
                    fields=[card.front, card.back, ""],
                    tags=card.tags,
                )
            else:
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

    logger.info(f"Created APKG at {output_path} with {len(media_files)} media files")

    # Clean up temp files
    for f in media_files:
        try:
            Path(f).unlink()
        except OSError:
            pass
    try:
        Path(temp_dir).rmdir()
    except OSError:
        pass

    return output_path


def _create_basic_model(model_id: int, deck_name: str) -> "genanki.Model":
    """Create a basic Anki model with Front/Back fields."""
    import genanki

    return genanki.Model(
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


def _create_model_with_evidence(model_id: int, deck_name: str) -> "genanki.Model":
    """Create an Anki model with Front/Back/Evidence fields."""
    import genanki

    return genanki.Model(
        model_id,
        f"{deck_name} Model",
        fields=[
            {"name": "Front"},
            {"name": "Back"},
            {"name": "Evidence"},
        ],
        templates=[
            {
                "name": "Card 1",
                "qfmt": "{{Front}}",
                "afmt": """{{FrontSide}}<hr id="answer">{{Back}}
{{#Evidence}}
<hr>
<div class="evidence">
    <div class="evidence-label">Source:</div>
    {{Evidence}}
</div>
{{/Evidence}}""",
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
        .evidence {
            margin-top: 20px;
            padding: 10px;
            background-color: #f5f5f5;
            border-radius: 8px;
        }
        .evidence-label {
            font-size: 12px;
            color: #666;
            margin-bottom: 8px;
        }
        .evidence img {
            max-width: 100%;
            border-radius: 4px;
            border: 1px solid #ddd;
        }
        """,
    )


def _create_evidence_html(
    evidence_list: list[Evidence],
    slide_images: dict[int, bytes],
    temp_dir: str,
    card_index: int,
) -> tuple[str, list[str]]:
    """Create HTML for evidence images and return media file paths.

    Args:
        evidence_list: List of evidence objects
        slide_images: Dict mapping slide index to image bytes
        temp_dir: Temporary directory for media files
        card_index: Index of the card (for unique filenames)

    Returns:
        Tuple of (HTML string, list of media file paths)
    """
    html_parts: list[str] = []
    media_files: list[str] = []

    for j, evidence in enumerate(evidence_list):
        slide_idx = evidence.slide_index
        if slide_idx is None or slide_idx not in slide_images:
            logger.debug(f"No image for slide {slide_idx}")
            continue

        slide_image = slide_images[slide_idx]

        # Try to crop the evidence region
        if evidence.bbox:
            try:
                cropped = crop_evidence(slide_image, evidence, padding=20)
                if cropped:
                    image_data = cropped
                else:
                    # Use full slide if crop failed
                    image_data = slide_image
            except CropError as e:
                logger.warning(f"Crop failed, using full slide: {e}")
                image_data = slide_image
        else:
            # No bbox, use full slide
            image_data = slide_image

        # Generate unique filename
        image_hash = hashlib.md5(image_data).hexdigest()[:8]
        filename = f"evidence_{card_index}_{j}_{image_hash}.png"
        filepath = Path(temp_dir) / filename

        # Write image to temp file
        filepath.write_bytes(image_data)
        media_files.append(str(filepath))

        # Generate HTML
        html_parts.append(f'<img src="{filename}" alt="Evidence from slide {slide_idx + 1}">')

        # Add text snippet if available
        if evidence.text_snippet:
            snippet = evidence.text_snippet[:200]
            if len(evidence.text_snippet) > 200:
                snippet += "..."
            html_parts.append(f'<div class="snippet">{snippet}</div>')

    return "\n".join(html_parts), media_files


def _generate_id(name: str) -> int:
    """Generate a deterministic ID from a string."""
    # Use hash to generate a consistent ID
    hash_bytes = hashlib.md5(name.encode()).digest()
    # Take first 4 bytes and convert to int, mask to 32 bits
    return int.from_bytes(hash_bytes[:4], "big") & 0x7FFFFFFF
