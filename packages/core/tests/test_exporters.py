"""Tests for export functionality."""

import tempfile
from pathlib import Path

import pytest

from slide2anki_core.exporters.apkg import _generate_id, export_apkg
from slide2anki_core.exporters.tsv import export_tsv
from slide2anki_core.schemas.cards import CardDraft, CardFlag, CardStatus
from slide2anki_core.schemas.claims import BoundingBox, Evidence


@pytest.fixture
def sample_cards() -> list[CardDraft]:
    """Create sample cards for testing."""
    return [
        CardDraft(
            front="What is the capital of France?",
            back="Paris",
            tags=["geography", "europe"],
            confidence=0.95,
            status=CardStatus.APPROVED,
            evidence=[
                Evidence(
                    slide_index=0,
                    bbox=BoundingBox(x=0.1, y=0.2, width=0.3, height=0.2),
                    text_snippet="The capital of France is Paris",
                )
            ],
        ),
        CardDraft(
            front="What is 2 + 2?",
            back="4",
            tags=["math"],
            confidence=0.99,
            status=CardStatus.APPROVED,
        ),
        CardDraft(
            front="Pending question?",
            back="Pending answer",
            tags=[],
            confidence=0.5,
            status=CardStatus.PENDING,
            flags=[CardFlag.NEEDS_REVIEW],
        ),
        CardDraft(
            front="Rejected question?",
            back="Rejected answer",
            tags=[],
            confidence=0.3,
            status=CardStatus.REJECTED,
        ),
    ]


class TestTSVExport:
    """Tests for TSV export."""

    def test_export_all_cards(self, sample_cards: list[CardDraft]) -> None:
        """Test exporting all cards to TSV."""
        result = export_tsv(sample_cards, only_approved=False)

        lines = result.strip().split("\n")
        # Should have all 4 cards (no header in TSV)
        assert len(lines) == 4

    def test_export_approved_only(self, sample_cards: list[CardDraft]) -> None:
        """Test exporting only approved cards."""
        result = export_tsv(sample_cards, only_approved=True)

        lines = result.strip().split("\n")
        # Should have only 2 approved cards
        assert len(lines) == 2
        assert "Paris" in lines[0]
        assert "4" in lines[1]

    def test_export_to_file(self, sample_cards: list[CardDraft]) -> None:
        """Test exporting to a file."""
        with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False) as f:
            output_path = Path(f.name)

        try:
            export_tsv(sample_cards, output=output_path)
            assert output_path.exists()

            content = output_path.read_text()
            assert "Paris" in content
        finally:
            output_path.unlink()

    def test_tags_in_output(self, sample_cards: list[CardDraft]) -> None:
        """Test that tags are included in TSV output."""
        result = export_tsv(sample_cards, only_approved=True)

        # Tags should be space-separated in the third column
        assert "geography europe" in result or "europe geography" in result


class TestAPKGExport:
    """Tests for APKG export."""

    def test_generate_id_deterministic(self) -> None:
        """Test that ID generation is deterministic."""
        id1 = _generate_id("Test Deck")
        id2 = _generate_id("Test Deck")
        assert id1 == id2

    def test_generate_id_unique(self) -> None:
        """Test that different names generate different IDs."""
        id1 = _generate_id("Deck A")
        id2 = _generate_id("Deck B")
        assert id1 != id2

    def test_export_basic(self, sample_cards: list[CardDraft]) -> None:
        """Test basic APKG export without images."""
        with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as f:
            output_path = Path(f.name)

        try:
            result_path = export_apkg(
                sample_cards,
                "Test Deck",
                output_path,
                only_approved=True,
                embed_evidence=False,
            )

            assert result_path == output_path
            assert output_path.exists()
            # APKG files are ZIP archives
            assert output_path.stat().st_size > 0
        finally:
            output_path.unlink()

    def test_export_approved_only(self, sample_cards: list[CardDraft]) -> None:
        """Test that only_approved filter works."""
        with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as f:
            output_path = Path(f.name)

        try:
            # This should only include the 2 approved cards
            result_path = export_apkg(
                sample_cards,
                "Test Deck",
                output_path,
                only_approved=True,
                embed_evidence=False,
            )

            assert result_path.exists()
        finally:
            output_path.unlink()

    def test_export_with_evidence_no_images(
        self, sample_cards: list[CardDraft]
    ) -> None:
        """Test export with evidence enabled but no slide images."""
        with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as f:
            output_path = Path(f.name)

        try:
            # Should work even without slide_images
            result_path = export_apkg(
                sample_cards,
                "Test Deck",
                output_path,
                embed_evidence=True,
                slide_images=None,
            )

            assert result_path.exists()
        finally:
            output_path.unlink()


class TestAPKGWithImages:
    """Tests for APKG export with embedded images."""

    @pytest.fixture
    def sample_image(self) -> bytes:
        """Create a minimal valid PNG image."""
        # Minimal 1x1 white PNG
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
            b"\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02"
            b"\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    def test_export_with_embedded_images(
        self, sample_cards: list[CardDraft], sample_image: bytes
    ) -> None:
        """Test export with embedded evidence images."""
        with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as f:
            output_path = Path(f.name)

        slide_images = {0: sample_image}

        try:
            result_path = export_apkg(
                sample_cards,
                "Test Deck",
                output_path,
                only_approved=True,
                slide_images=slide_images,
                embed_evidence=True,
            )

            assert result_path.exists()
            # File should be larger due to embedded images
            assert output_path.stat().st_size > 100
        finally:
            output_path.unlink()
