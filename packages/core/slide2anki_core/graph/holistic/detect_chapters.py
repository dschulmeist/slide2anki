"""Chapter detection and organization node.

This module analyzes the extracted markdown content to identify logical
chapters or sections. Chapters can be detected from:

1. Explicit markdown headers (## Section Title)
2. Table of contents patterns in the original slides
3. Topic transitions detected by analyzing content flow

The chapter structure is used to organize the final markdown document
and to group related flashcards together.
"""

import re
from collections.abc import Callable
from typing import Any

from slide2anki_core.graph.config import HolisticConfig
from slide2anki_core.schemas.chapters import Chapter, ChapterOutline
from slide2anki_core.utils.hashing import content_hash
from slide2anki_core.utils.logging import get_logger

logger = get_logger(__name__)


def _extract_headers_from_markdown(markdown: str) -> list[tuple[int, str, int]]:
    """Extract all headers from markdown content with their positions.

    Args:
        markdown: Raw markdown content

    Returns:
        List of (level, title, line_number) tuples
    """
    headers: list[tuple[int, str, int]] = []
    lines = markdown.split("\n")

    for i, line in enumerate(lines):
        # Match markdown headers (## or ###)
        match = re.match(r"^(#{1,4})\s+(.+)$", line.strip())
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            headers.append((level, title, i))

    return headers


def _create_chapters_from_headers(
    headers: list[tuple[int, str, int]],
    total_lines: int,
    document_name: str,
) -> list[Chapter]:
    """Create Chapter objects from extracted headers.

    Args:
        headers: List of (level, title, line_number) tuples
        total_lines: Total number of lines in the document
        document_name: Name of the source document

    Returns:
        List of Chapter objects
    """
    if not headers:
        # No headers found - create a single chapter for the whole document
        return [
            Chapter(
                chapter_id=content_hash(f"chapter:0:{document_name}")[:12],
                title=document_name,
                order=0,
                start_slide=0,
                end_slide=0,  # Will be updated later
                summary=None,
                parent_chapter_id=None,
            )
        ]

    chapters: list[Chapter] = []
    top_level = min(h[0] for h in headers)  # Find the highest level (smallest number)

    # Filter to only top-level headers for main chapters
    main_headers = [
        (title, line) for level, title, line in headers if level == top_level
    ]

    for i, (title, line_num) in enumerate(main_headers):
        # Calculate end line (start of next chapter or end of document)
        if i + 1 < len(main_headers):
            end_line = main_headers[i + 1][1] - 1
        else:
            end_line = total_lines - 1

        chapter = Chapter(
            chapter_id=content_hash(f"chapter:{i}:{title}")[:12],
            title=title,
            order=i,
            start_slide=line_num,  # Using line number as proxy for "slide"
            end_slide=end_line,
            summary=None,
            parent_chapter_id=None,
        )
        chapters.append(chapter)

    return chapters


def _detect_toc_structure(markdown: str) -> list[str] | None:
    """Try to detect a table of contents structure in the markdown.

    Looks for patterns like:
    - "Content of this lecture"
    - Numbered lists at the beginning
    - Patterns like "1. Topic A, 2. Topic B"

    Args:
        markdown: Raw markdown content

    Returns:
        List of detected chapter titles, or None if no TOC found
    """
    # Look for "Content" or "Contents" or "Outline" sections
    toc_patterns = [
        r"(?i)content[s]?\s+of\s+(?:this|the)\s+lecture",
        r"(?i)lecture\s+content[s]?",
        r"(?i)outline",
        r"(?i)agenda",
        r"(?i)topics?\s+covered",
    ]

    for pattern in toc_patterns:
        match = re.search(pattern, markdown)
        if match:
            # Found a TOC indicator - look for list items after it
            start_pos = match.end()
            # Look for the next section of content
            section_text = markdown[start_pos : start_pos + 1000]

            # Extract list items (bullets or numbers)
            items = re.findall(
                r"(?:^|\n)\s*(?:[-*•]|\d+[.):])\s*(.+?)(?=\n|$)",
                section_text,
            )

            if items and len(items) >= 2:
                # Clean up items
                cleaned = [item.strip() for item in items if item.strip()]
                # Filter out check marks and generic items
                cleaned = [
                    item
                    for item in cleaned
                    if not re.match(r"^[✓✔☑]", item) and len(item) > 3
                ]
                if cleaned:
                    logger.info(f"Detected TOC with {len(cleaned)} items")
                    return cleaned

    return None


def _reorganize_by_chapters(
    markdown: str,
    chapters: list[Chapter],
) -> str:
    """Reorganize markdown content by detected chapters.

    Ensures consistent formatting and structure.

    Args:
        markdown: Raw markdown content
        chapters: Detected chapter structure

    Returns:
        Reorganized markdown content
    """
    if len(chapters) <= 1:
        # Single chapter or no structure - return as is
        return markdown

    # The markdown should already be organized by the extraction
    # This function mainly ensures consistent formatting

    lines = markdown.split("\n")
    result_lines: list[str] = []

    # Add document-level structure if needed
    for chapter in chapters:
        # Find the chapter's content range
        start_line = chapter.start_slide
        end_line = chapter.end_slide

        if start_line < len(lines):
            # Add chapter header if not already present
            first_line = lines[start_line].strip()
            if not first_line.startswith("##"):
                result_lines.append(f"## {chapter.title}")
                result_lines.append("")

            # Add chapter content
            chapter_lines = lines[start_line : end_line + 1]
            result_lines.extend(chapter_lines)
            result_lines.append("")

    return "\n".join(result_lines)


def create_detect_chapters_node(
    config: HolisticConfig | None = None,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create a chapter detection node for the holistic pipeline.

    This node analyzes the extracted markdown to identify logical
    chapters or sections, either from explicit headers or from
    detected table of contents structure.

    Args:
        config: Holistic processing configuration

    Returns:
        Node function for the LangGraph pipeline
    """
    resolved_config = config or HolisticConfig()

    def detect_chapters_node(state: dict[str, Any]) -> dict[str, Any]:
        """Detect and organize chapters in the extracted content.

        Args:
            state: Pipeline state with raw_markdown

        Returns:
            Updated state with chapter_outline and organized_markdown
        """
        raw_markdown: str = state.get("raw_markdown", "")
        document = state.get("document")
        document_name = document.name if document else "Document"
        slides = state.get("slides", [])

        if not raw_markdown:
            logger.warning("No markdown content for chapter detection")
            return {
                **state,
                "chapter_outline": ChapterOutline(
                    document_name=document_name,
                    chapters=[],
                    total_slides=len(slides),
                ),
                "organized_markdown": "",
                "current_step": "detect_chapters",
                "progress": 55,
            }

        chapters: list[Chapter] = []

        # Try to detect TOC structure first if enabled
        if resolved_config.use_toc_if_present:
            toc_items = _detect_toc_structure(raw_markdown)
            if toc_items:
                # Create chapters from TOC items
                for i, title in enumerate(toc_items):
                    chapters.append(
                        Chapter(
                            chapter_id=content_hash(f"toc:{i}:{title}")[:12],
                            title=title,
                            order=i,
                            start_slide=0,  # TOC-based chapters don't have precise bounds
                            end_slide=len(slides) - 1,
                            summary=None,
                            parent_chapter_id=None,
                        )
                    )

        # If no TOC found, detect from markdown headers
        if not chapters and resolved_config.detect_chapters:
            headers = _extract_headers_from_markdown(raw_markdown)
            total_lines = len(raw_markdown.split("\n"))
            chapters = _create_chapters_from_headers(
                headers, total_lines, document_name
            )

        # Create chapter outline
        chapter_outline = ChapterOutline(
            document_name=document_name,
            chapters=chapters,
            total_slides=len(slides),
        )

        # Reorganize markdown by chapters
        organized_markdown = _reorganize_by_chapters(raw_markdown, chapters)

        logger.info(f"Detected {len(chapters)} chapters in document '{document_name}'")

        return {
            **state,
            "chapter_outline": chapter_outline,
            "organized_markdown": organized_markdown,
            "current_step": "detect_chapters",
            "progress": 55,
        }

    return detect_chapters_node
