"""Tests for PDF validation utilities."""

import pytest

from slide2anki_core.utils.pdf import PDFValidationError, get_pdf_info, validate_pdf


class TestPDFValidation:
    """Tests for PDF validation."""

    def test_valid_pdf_header(self) -> None:
        """Test that valid PDF header passes validation."""
        # Minimal PDF-like content
        pdf_data = b"%PDF-1.7\n%%EOF"
        assert validate_pdf(pdf_data) is True

    def test_empty_data_raises(self) -> None:
        """Test that empty data raises error."""
        with pytest.raises(PDFValidationError, match="Empty file data"):
            validate_pdf(b"")

    def test_too_short_raises(self) -> None:
        """Test that data too short raises error."""
        with pytest.raises(PDFValidationError, match="too small"):
            validate_pdf(b"abc")

    def test_invalid_magic_raises(self) -> None:
        """Test that invalid magic bytes raise error."""
        with pytest.raises(PDFValidationError, match="magic bytes"):
            validate_pdf(b"NOT A PDF FILE")

    def test_png_rejected(self) -> None:
        """Test that PNG files are rejected."""
        png_header = b"\x89PNG\r\n\x1a\n"
        with pytest.raises(PDFValidationError, match="magic bytes"):
            validate_pdf(png_header)

    def test_jpeg_rejected(self) -> None:
        """Test that JPEG files are rejected."""
        jpeg_header = b"\xff\xd8\xff\xe0"
        with pytest.raises(PDFValidationError, match="magic bytes"):
            validate_pdf(jpeg_header)


class TestPDFInfo:
    """Tests for PDF info extraction."""

    def test_extract_version(self) -> None:
        """Test version extraction from header."""
        pdf_data = b"%PDF-1.7\n%%EOF"
        info = get_pdf_info(pdf_data)

        assert info["version"] == "1.7"
        assert info["size_bytes"] == len(pdf_data)

    def test_version_1_4(self) -> None:
        """Test version 1.4 extraction."""
        pdf_data = b"%PDF-1.4\r\n%%EOF"
        info = get_pdf_info(pdf_data)

        assert info["version"] == "1.4"

    def test_size_calculation(self) -> None:
        """Test that size is correctly reported."""
        pdf_data = b"%PDF-1.7" + b"\x00" * 1000 + b"%%EOF"
        info = get_pdf_info(pdf_data)

        assert info["size_bytes"] == len(pdf_data)
