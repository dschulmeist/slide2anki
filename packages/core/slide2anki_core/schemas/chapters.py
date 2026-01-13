"""Chapter detection and organization schemas.

This module defines schemas for detecting and organizing document content
into logical chapters. Chapters provide structure to the extracted markdown,
grouping related content together based on the document's natural organization.
"""

from pydantic import BaseModel, Field


class Chapter(BaseModel):
    """A logical chapter or section in the document.

    Chapters are detected from the document content based on:
    - Explicit section headings in slides
    - Topic transitions detected by the model
    - Table of contents if present

    Each chapter groups related markdown content together.
    """

    chapter_id: str = Field(..., description="Unique identifier for this chapter")
    title: str = Field(..., description="Chapter title")
    order: int = Field(..., description="Position in chapter sequence (0-based)")
    start_slide: int = Field(
        ..., description="First slide index belonging to this chapter (0-based)"
    )
    end_slide: int = Field(
        ..., description="Last slide index belonging to this chapter (0-based)"
    )
    summary: str | None = Field(
        None, description="Brief summary of chapter content (optional)"
    )
    parent_chapter_id: str | None = Field(
        None, description="Parent chapter ID for nested sections (optional)"
    )


class ChapterOutline(BaseModel):
    """The complete chapter structure for a document.

    Represents the hierarchical organization of the document into chapters,
    detected from analyzing the full document content.
    """

    document_name: str = Field(..., description="Name of the source document")
    chapters: list[Chapter] = Field(
        default_factory=list, description="Ordered list of chapters"
    )
    total_slides: int = Field(..., description="Total number of slides in document")

    def get_chapter_for_slide(self, slide_index: int) -> Chapter | None:
        """Find the chapter containing a given slide.

        Args:
            slide_index: The slide index to look up

        Returns:
            The Chapter containing this slide, or None if not found
        """
        for chapter in self.chapters:
            if chapter.start_slide <= slide_index <= chapter.end_slide:
                return chapter
        return None

    def get_chapter_by_id(self, chapter_id: str) -> Chapter | None:
        """Find a chapter by its ID.

        Args:
            chapter_id: The chapter ID to look up

        Returns:
            The matching Chapter, or None if not found
        """
        for chapter in self.chapters:
            if chapter.chapter_id == chapter_id:
                return chapter
        return None


class DocumentChunk(BaseModel):
    """A chunk of slides for processing with overlap.

    The holistic pipeline processes documents in chunks to handle
    large documents that exceed model context limits. Chunks have
    configurable overlap to maintain context across boundaries.
    """

    chunk_index: int = Field(..., description="Position in chunk sequence (0-based)")
    start_slide: int = Field(
        ..., description="First slide index in this chunk (0-based)"
    )
    end_slide: int = Field(..., description="Last slide index in this chunk (0-based)")
    slide_indices: list[int] = Field(..., description="All slide indices in this chunk")
    is_first: bool = Field(False, description="True if this is the first chunk")
    is_last: bool = Field(False, description="True if this is the last chunk")
    overlap_start: int = Field(
        0, description="Number of slides overlapping with previous chunk"
    )
    overlap_end: int = Field(
        0, description="Number of slides overlapping with next chunk"
    )

    @property
    def size(self) -> int:
        """Number of slides in this chunk."""
        return len(self.slide_indices)


class ChunkingConfig(BaseModel):
    """Configuration for document chunking strategy.

    Controls how large documents are split into chunks for processing,
    including overlap ratio to maintain context across chunk boundaries.
    """

    target_chunk_size: int = Field(
        10, ge=1, description="Target number of slides per chunk"
    )
    overlap_ratio: float = Field(
        0.15,
        ge=0.0,
        le=0.5,
        description="Fraction of chunk size to overlap (default 15%)",
    )
    min_chunk_size: int = Field(
        3, ge=1, description="Minimum slides per chunk (avoid tiny chunks)"
    )
    max_chunk_size: int = Field(
        20, ge=1, description="Maximum slides per chunk (avoid context overflow)"
    )

    def calculate_overlap(self) -> int:
        """Calculate the number of overlapping slides between chunks.

        Returns:
            Number of slides to overlap (minimum 1 if overlap_ratio > 0)
        """
        overlap = int(self.target_chunk_size * self.overlap_ratio)
        # Ensure at least 1 slide overlap if ratio > 0
        if self.overlap_ratio > 0 and overlap < 1:
            overlap = 1
        return overlap

    def create_chunks(self, total_slides: int) -> list[DocumentChunk]:
        """Create chunks for a document with the specified number of slides.

        Args:
            total_slides: Total number of slides in the document

        Returns:
            List of DocumentChunk objects covering all slides
        """
        if total_slides <= 0:
            return []

        # Small documents don't need chunking
        if total_slides <= self.target_chunk_size:
            return [
                DocumentChunk(
                    chunk_index=0,
                    start_slide=0,
                    end_slide=total_slides - 1,
                    slide_indices=list(range(total_slides)),
                    is_first=True,
                    is_last=True,
                    overlap_start=0,
                    overlap_end=0,
                )
            ]

        chunks: list[DocumentChunk] = []
        overlap = self.calculate_overlap()
        step = self.target_chunk_size - overlap

        # Ensure step is at least 1 to make progress
        if step < 1:
            step = 1

        chunk_index = 0
        start = 0

        while start < total_slides:
            end = min(start + self.target_chunk_size - 1, total_slides - 1)

            # Determine overlap values
            overlap_start = 0 if start == 0 else overlap
            overlap_end = 0 if end >= total_slides - 1 else overlap

            chunk = DocumentChunk(
                chunk_index=chunk_index,
                start_slide=start,
                end_slide=end,
                slide_indices=list(range(start, end + 1)),
                is_first=(start == 0),
                is_last=(end >= total_slides - 1),
                overlap_start=overlap_start,
                overlap_end=overlap_end,
            )
            chunks.append(chunk)

            # Move to next chunk
            start += step
            chunk_index += 1

            # Avoid infinite loop
            if start <= chunks[-1].start_slide:
                break

        return chunks
