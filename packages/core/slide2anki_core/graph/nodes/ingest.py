"""Ingest node: Load and validate PDF input."""

from pathlib import Path
from typing import Any

from slide2anki_core.schemas.document import Document
from slide2anki_core.utils.logging import get_logger
from slide2anki_core.utils.pdf import PDFValidationError, get_pdf_info, validate_pdf

logger = get_logger(__name__)


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

    logger.info(f"Ingesting PDF (path={pdf_path}, has_data={pdf_data is not None})")

    if pdf_path:
        path = Path(pdf_path)
        if not path.exists():
            error_msg = f"PDF not found: {pdf_path}"
            logger.error(error_msg)
            return {
                **state,
                "errors": state.get("errors", []) + [error_msg],
                "current_step": "ingest",
                "progress": 0,
            }
        try:
            pdf_data = path.read_bytes()
            logger.info(f"Read PDF from {pdf_path} ({len(pdf_data)} bytes)")
        except OSError as e:
            error_msg = f"Failed to read PDF: {e}"
            logger.error(error_msg)
            return {
                **state,
                "errors": state.get("errors", []) + [error_msg],
                "current_step": "ingest",
                "progress": 0,
            }
        if not deck_name or deck_name == "Untitled Deck":
            deck_name = path.stem

    if not pdf_data:
        error_msg = "No PDF data provided"
        logger.error(error_msg)
        return {
            **state,
            "errors": state.get("errors", []) + [error_msg],
            "current_step": "ingest",
            "progress": 0,
        }

    # Validate PDF
    try:
        validate_pdf(pdf_data)
        pdf_info = get_pdf_info(pdf_data)
        logger.info(
            f"PDF validated: version={pdf_info.get('version')}, size={pdf_info.get('size_bytes')} bytes"
        )
    except PDFValidationError as e:
        error_msg = f"Invalid PDF: {e}"
        logger.error(error_msg)
        return {
            **state,
            "errors": state.get("errors", []) + [error_msg],
            "current_step": "ingest",
            "progress": 0,
        }

    # Create document object
    document = Document(
        name=deck_name,
        pdf_path=Path(pdf_path) if pdf_path else None,
        pdf_data=pdf_data,
    )

    logger.info(f"Created document: {deck_name}")

    return {
        **state,
        "document": document,
        "current_step": "ingest",
        "progress": 5,
        "errors": state.get("errors", []),
    }
