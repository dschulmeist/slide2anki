"""Configuration helpers for LangGraph pipelines.

This module provides configuration dataclasses for controlling pipeline behavior,
including both the legacy per-slide extraction pipeline and the new holistic
document processing pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from slide2anki_core.schemas.chapters import ChunkingConfig


@dataclass(frozen=True)
class GraphConfig:
    """Configuration values for graph loops and concurrency.

    This config controls the legacy per-slide extraction pipeline behavior.
    For new projects, prefer using HolisticConfig with the holistic pipeline.
    """

    # Repair loop limits
    max_claim_repairs: int = 2
    max_card_repairs: int = 2

    # Concurrency control
    max_slide_concurrency: int = 2

    # Fast mode: skip verification and repair loops for speed
    fast_mode: bool = True

    # Skip segmentation for slides with simple layouts (fewer API calls)
    skip_simple_segmentation: bool = True


@dataclass(frozen=True)
class HolisticConfig:
    """Configuration for the holistic document processing pipeline.

    The holistic pipeline processes entire documents as a coherent unit rather
    than extracting claims per-slide. This produces higher quality markdown
    with natural deduplication and proper context.
    """

    # Chunking configuration
    chunk_size: int = 10  # Target slides per chunk
    chunk_overlap: float = 0.15  # 15% overlap between chunks

    # Image filtering thresholds
    header_threshold: float = 0.15  # Top 15% is header region
    footer_threshold: float = 0.15  # Bottom 15% is footer region
    min_image_area: float = 0.05  # Minimum 5% of slide area
    repetition_threshold: float = 0.5  # Skip if on >50% of slides

    # Processing options
    extract_images: bool = True  # Whether to extract and process images
    transcribe_formulas: bool = True  # Transcribe formula images to LaTeX
    describe_diagrams: bool = True  # Generate descriptions for diagrams
    embed_complex_images: bool = True  # Embed images that can't be transcribed

    # Card generation (same as GraphConfig for compatibility)
    max_card_repairs: int = 2

    # Chapter detection
    detect_chapters: bool = True  # Auto-detect chapter structure
    use_toc_if_present: bool = True  # Prefer table of contents for chapters

    def to_chunking_config(self) -> ChunkingConfig:
        """Convert to a ChunkingConfig for the chunking module.

        Returns:
            ChunkingConfig instance with matching settings
        """
        # Import here to avoid circular imports at runtime
        from slide2anki_core.schemas.chapters import (
            ChunkingConfig as ChunkingConfigClass,
        )

        return ChunkingConfigClass(
            target_chunk_size=self.chunk_size,
            overlap_ratio=self.chunk_overlap,
        )
