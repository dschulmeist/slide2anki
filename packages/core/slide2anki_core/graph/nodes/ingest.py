"""Ingest node: Load and validate PDF input."""

from pathlib import Path
from typing import Any

from slide2anki_core.schemas.document import Document


def ingest_node(state: dict[str, Any]) -> dict[str, Any]:
    """Load PDF and create document object.

    Args:
        state: Pipeline state with pdf_path or pdf_data

    Returns:
        Updated state with document object
    """
    pdf_path = state.get("pdf_path")
    pdf_data = state.get("pdf_data")
    deck_name = state.get("deck_name", "Untitled Deck")

    if pdf_path:
        path = Path(pdf_path)
        if not path.exists():
            return {
                **state,
                "errors": state.get("errors", []) + [f"PDF not found: {pdf_path}"],
                "current_step": "ingest",
                "progress": 0,
            }
        pdf_data = path.read_bytes()
        if not deck_name or deck_name == "Untitled Deck":
            deck_name = path.stem

    if not pdf_data:
        return {
            **state,
            "errors": state.get("errors", []) + ["No PDF data provided"],
            "current_step": "ingest",
            "progress": 0,
        }

    # Create document object
    document = Document(
        name=deck_name,
        pdf_path=Path(pdf_path) if pdf_path else None,
        pdf_data=pdf_data,
    )

    return {
        **state,
        "document": document,
        "current_step": "ingest",
        "progress": 5,
        "errors": state.get("errors", []),
    }
