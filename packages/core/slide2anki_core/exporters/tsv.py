"""TSV export for Anki import."""

import csv
from io import StringIO
from pathlib import Path

from slide2anki_core.schemas.cards import CardDraft, CardStatus


def export_tsv(
    cards: list[CardDraft],
    output: str | Path | None = None,
    include_tags: bool = True,
    only_approved: bool = False,
) -> str:
    """Export cards to TSV format for Anki import.

    Args:
        cards: List of card drafts
        output: Optional output path (if None, returns string)
        include_tags: Include tags column
        only_approved: Only export approved cards

    Returns:
        TSV content as string
    """
    # Filter cards if needed
    if only_approved:
        cards = [c for c in cards if c.status == CardStatus.APPROVED]

    # Create TSV content
    buffer = StringIO()
    writer = csv.writer(buffer, delimiter="\t", quoting=csv.QUOTE_MINIMAL)

    for card in cards:
        row = [card.front, card.back]
        if include_tags and card.tags:
            row.append(" ".join(card.tags))
        writer.writerow(row)

    content = buffer.getvalue()

    # Write to file if path provided
    if output:
        path = Path(output)
        path.write_text(content, encoding="utf-8")

    return content
