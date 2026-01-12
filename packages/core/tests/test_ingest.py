"""Tests for ingest node functionality."""

import tempfile
from pathlib import Path

import pytest

from slide2anki_core.graph.nodes.ingest import ingest_node


class TestIngestNode:
    """Tests for the ingest node."""

    def test_ingest_from_bytes(self) -> None:
        """Test ingesting PDF from bytes."""
        pdf_data = b"%PDF-1.7\n%%EOF"
        state = {
            "pdf_data": pdf_data,
            "deck_name": "Test Deck",
        }

        result = ingest_node(state)

        assert "document" in result
        assert result["document"].name == "Test Deck"
        assert result["document"].pdf_data == pdf_data
        assert result["progress"] == 5
        assert result["current_step"] == "ingest"

    def test_ingest_from_file(self) -> None:
        """Test ingesting PDF from file path."""
        pdf_data = b"%PDF-1.7\n%%EOF"

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_data)
            pdf_path = f.name

        try:
            state = {
                "pdf_path": pdf_path,
            }

            result = ingest_node(state)

            assert "document" in result
            # Deck name should be derived from file name
            assert result["document"].name == Path(pdf_path).stem
            assert result["document"].pdf_data == pdf_data
        finally:
            Path(pdf_path).unlink()

    def test_ingest_missing_file(self) -> None:
        """Test that missing file produces error."""
        state = {
            "pdf_path": "/nonexistent/path/to/file.pdf",
        }

        result = ingest_node(state)

        assert "errors" in result
        assert len(result["errors"]) > 0
        assert "not found" in result["errors"][0].lower()
        assert result["progress"] == 0

    def test_ingest_no_data(self) -> None:
        """Test that missing data produces error."""
        state = {}

        result = ingest_node(state)

        assert "errors" in result
        assert len(result["errors"]) > 0
        assert "no pdf data" in result["errors"][0].lower()

    def test_ingest_invalid_pdf(self) -> None:
        """Test that invalid PDF produces error."""
        state = {
            "pdf_data": b"NOT A PDF FILE",
            "deck_name": "Test Deck",
        }

        result = ingest_node(state)

        assert "errors" in result
        assert len(result["errors"]) > 0
        assert "invalid" in result["errors"][0].lower()

    def test_ingest_preserves_existing_errors(self) -> None:
        """Test that existing errors are preserved."""
        state = {
            "pdf_data": b"NOT A PDF FILE",
            "errors": ["Previous error"],
        }

        result = ingest_node(state)

        assert "errors" in result
        assert "Previous error" in result["errors"]
        assert len(result["errors"]) == 2

    def test_ingest_custom_deck_name(self) -> None:
        """Test that custom deck name is used."""
        pdf_data = b"%PDF-1.7\n%%EOF"

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_data)
            pdf_path = f.name

        try:
            state = {
                "pdf_path": pdf_path,
                "deck_name": "My Custom Deck",
            }

            result = ingest_node(state)

            assert result["document"].name == "My Custom Deck"
        finally:
            Path(pdf_path).unlink()
