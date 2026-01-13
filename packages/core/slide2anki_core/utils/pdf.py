"""PDF validation utilities."""

from slide2anki_core.utils.logging import get_logger

logger = get_logger(__name__)

# PDF magic bytes
PDF_MAGIC = b"%PDF"


class PDFValidationError(Exception):
    """Error when PDF validation fails."""

    pass


def validate_pdf(data: bytes) -> bool:
    """Validate that data is a valid PDF file.

    Args:
        data: Raw file bytes

    Returns:
        True if valid PDF

    Raises:
        PDFValidationError: If validation fails
    """
    if not data:
        raise PDFValidationError("Empty file data")

    if len(data) < 4:
        raise PDFValidationError("File too small to be a valid PDF")

    # Check magic bytes
    if not data[:4].startswith(PDF_MAGIC):
        raise PDFValidationError(
            f"Invalid PDF: file does not start with PDF magic bytes. Got: {data[:4]!r}"
        )

    # Check for PDF EOF marker (optional but recommended)
    # PDFs should end with %%EOF
    if b"%%EOF" not in data[-1024:]:
        logger.warning("PDF does not contain %%EOF marker near end of file")

    logger.debug(f"PDF validation passed ({len(data)} bytes)")
    return True


def get_pdf_info(data: bytes) -> dict[str, str | int | None]:
    """Extract basic info from PDF data.

    Args:
        data: Raw PDF bytes

    Returns:
        Dict with PDF metadata
    """
    info: dict[str, str | int | None] = {
        "size_bytes": len(data),
        "version": None,
        "page_count": None,
    }

    # Extract PDF version from header
    # Format: %PDF-1.7
    try:
        header = data[:20].decode("latin-1")
        if header.startswith("%PDF-"):
            version_end = header.find("\n")
            if version_end == -1:
                version_end = header.find("\r")
            if version_end == -1:
                version_end = 8
            info["version"] = header[5:version_end].strip()
    except (UnicodeDecodeError, IndexError):
        pass

    logger.debug(f"PDF info: {info}")
    return info
