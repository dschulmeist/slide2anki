"""Tests for the holistic document processing pipeline.

This module tests the new holistic pipeline that processes documents as
coherent units rather than per-slide extraction.
"""

from slide2anki_core.graph import HolisticConfig, build_holistic_graph
from slide2anki_core.schemas.chapters import ChunkingConfig, DocumentChunk


class TestChunkingConfig:
    """Tests for the ChunkingConfig schema."""

    def test_create_chunks_small_document(self):
        """Test that small documents get a single chunk."""
        config = ChunkingConfig(target_chunk_size=10, overlap_ratio=0.15)
        chunks = config.create_chunks(5)

        assert len(chunks) == 1
        assert chunks[0].is_first is True
        assert chunks[0].is_last is True
        assert chunks[0].slide_indices == [0, 1, 2, 3, 4]

    def test_create_chunks_exact_size(self):
        """Test chunking when document exactly matches chunk size."""
        config = ChunkingConfig(target_chunk_size=10, overlap_ratio=0.15)
        chunks = config.create_chunks(10)

        assert len(chunks) == 1
        assert chunks[0].slide_indices == list(range(10))

    def test_create_chunks_with_overlap(self):
        """Test that overlap is correctly applied between chunks."""
        config = ChunkingConfig(target_chunk_size=10, overlap_ratio=0.2)  # 2 slide overlap
        chunks = config.create_chunks(20)

        assert len(chunks) >= 2
        # First chunk should start at 0
        assert chunks[0].start_slide == 0
        # Second chunk should start before first chunk ends (overlap)
        if len(chunks) > 1:
            assert chunks[1].start_slide < chunks[0].end_slide + 1

    def test_create_chunks_empty_document(self):
        """Test handling of empty documents."""
        config = ChunkingConfig(target_chunk_size=10, overlap_ratio=0.15)
        chunks = config.create_chunks(0)

        assert len(chunks) == 0

    def test_overlap_calculation(self):
        """Test that overlap is calculated correctly."""
        config = ChunkingConfig(target_chunk_size=10, overlap_ratio=0.15)
        overlap = config.calculate_overlap()

        # 15% of 10 = 1.5, rounds to 1
        assert overlap == 1

    def test_overlap_minimum(self):
        """Test that overlap is at least 1 when ratio > 0."""
        config = ChunkingConfig(target_chunk_size=5, overlap_ratio=0.1)  # 0.5, rounds to 0
        overlap = config.calculate_overlap()

        # Should be at least 1 when ratio > 0
        assert overlap >= 1


class TestHolisticConfig:
    """Tests for the HolisticConfig dataclass."""

    def test_default_values(self):
        """Test that defaults are sensible."""
        config = HolisticConfig()

        assert config.chunk_size == 10
        assert config.chunk_overlap == 0.15
        assert config.header_threshold == 0.15
        assert config.footer_threshold == 0.15
        assert config.min_image_area == 0.05
        assert config.repetition_threshold == 0.5
        assert config.extract_images is True
        assert config.transcribe_formulas is True
        assert config.describe_diagrams is True
        assert config.detect_chapters is True

    def test_to_chunking_config(self):
        """Test conversion to ChunkingConfig."""
        holistic_config = HolisticConfig(chunk_size=15, chunk_overlap=0.2)
        chunking_config = holistic_config.to_chunking_config()

        assert chunking_config.target_chunk_size == 15
        assert chunking_config.overlap_ratio == 0.2


class TestDocumentChunk:
    """Tests for the DocumentChunk schema."""

    def test_chunk_size_property(self):
        """Test that size is calculated correctly."""
        chunk = DocumentChunk(
            chunk_index=0,
            start_slide=0,
            end_slide=9,
            slide_indices=list(range(10)),
            is_first=True,
            is_last=False,
        )

        assert chunk.size == 10

    def test_overlap_tracking(self):
        """Test that overlap values are tracked correctly."""
        chunk = DocumentChunk(
            chunk_index=1,
            start_slide=8,
            end_slide=17,
            slide_indices=list(range(8, 18)),
            is_first=False,
            is_last=False,
            overlap_start=2,
            overlap_end=2,
        )

        assert chunk.overlap_start == 2
        assert chunk.overlap_end == 2
        assert chunk.is_first is False
        assert chunk.is_last is False


class TestBuildHolisticGraph:
    """Tests for the build_holistic_graph function."""

    def test_build_graph_returns_compiled_graph(self):
        """Test that build_holistic_graph returns a compiled StateGraph."""
        # Create a mock adapter (we're just testing graph construction)
        from unittest.mock import MagicMock

        mock_adapter = MagicMock()

        graph = build_holistic_graph(mock_adapter)

        # Verify it's a compiled graph (has nodes attribute)
        assert graph is not None
        # LangGraph compiled graphs have get_graph method
        assert hasattr(graph, "ainvoke")

    def test_build_graph_with_custom_config(self):
        """Test that custom config is respected."""
        from unittest.mock import MagicMock

        mock_adapter = MagicMock()
        config = HolisticConfig(
            chunk_size=5,
            chunk_overlap=0.25,
            extract_images=False,
        )

        graph = build_holistic_graph(mock_adapter, config=config)

        assert graph is not None
