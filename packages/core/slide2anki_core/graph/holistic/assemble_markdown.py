"""Markdown assembly node for the holistic pipeline.

This module combines the organized markdown content with processed images
to create the final markdown document. It:

1. Parses the markdown into blocks (paragraphs, sections)
2. Embeds transcribed formulas, code, and tables in appropriate locations
3. Adds image descriptions and embedded images where relevant
4. Creates MarkdownBlock objects for compatibility with the card generation pipeline
5. Generates the final formatted markdown document with evidence links
"""

import re
from collections.abc import Callable
from typing import Any

from slide2anki_core.graph.config import HolisticConfig
from slide2anki_core.schemas.chapters import Chapter, ChapterOutline
from slide2anki_core.schemas.claims import Evidence
from slide2anki_core.schemas.images import ProcessedImage
from slide2anki_core.schemas.markdown import MarkdownBlock
from slide2anki_core.utils.hashing import content_hash
from slide2anki_core.utils.logging import get_logger

logger = get_logger(__name__)


def _parse_markdown_to_blocks(
    markdown: str,
    chapter_outline: ChapterOutline,
) -> list[dict[str, Any]]:
    """Parse markdown into block structures.

    Blocks are meaningful units of content:
    - Paragraphs
    - List items
    - Code blocks
    - Math blocks
    - Tables

    Args:
        markdown: Organized markdown content
        chapter_outline: Chapter structure for context

    Returns:
        List of block dicts with content, type, and chapter info
    """
    blocks: list[dict[str, Any]] = []
    lines = markdown.split("\n")

    current_chapter = chapter_outline.chapters[0] if chapter_outline.chapters else None
    current_block_lines: list[str] = []
    current_block_type = "paragraph"
    in_code_block = False
    in_math_block = False

    def flush_block() -> None:
        """Add current block to results if non-empty."""
        nonlocal current_block_lines, current_block_type
        if current_block_lines:
            content = "\n".join(current_block_lines).strip()
            if content:
                blocks.append(
                    {
                        "content": content,
                        "type": current_block_type,
                        "chapter": current_chapter,
                    }
                )
        current_block_lines = []
        current_block_type = "paragraph"

    for line in lines:
        stripped = line.strip()

        # Track chapter transitions
        if stripped.startswith("## "):
            flush_block()
            title = stripped[3:].strip()
            # Find matching chapter
            for ch in chapter_outline.chapters:
                if ch.title == title:
                    current_chapter = ch
                    break
            continue  # Don't include headers in blocks

        # Handle code blocks
        if stripped.startswith("```"):
            if in_code_block:
                current_block_lines.append(line)
                flush_block()
                in_code_block = False
            else:
                flush_block()
                in_code_block = True
                current_block_type = "code"
                current_block_lines.append(line)
            continue

        if in_code_block:
            current_block_lines.append(line)
            continue

        # Handle math blocks
        if stripped.startswith("$$"):
            if in_math_block:
                current_block_lines.append(line)
                flush_block()
                in_math_block = False
            else:
                flush_block()
                in_math_block = True
                current_block_type = "formula"
                current_block_lines.append(line)
            continue

        if in_math_block:
            current_block_lines.append(line)
            continue

        # Handle lists
        if re.match(r"^[-*•]\s+", stripped) or re.match(r"^\d+[.)]\s+", stripped):
            if current_block_type != "list":
                flush_block()
                current_block_type = "list"
            current_block_lines.append(line)
            continue

        # Handle tables
        if "|" in stripped and re.match(r"^\|.*\|$", stripped):
            if current_block_type != "table":
                flush_block()
                current_block_type = "table"
            current_block_lines.append(line)
            continue

        # Handle empty lines (paragraph separators)
        if not stripped:
            flush_block()
            continue

        # Regular paragraph content
        if current_block_type not in ("paragraph", "list"):
            flush_block()
        current_block_lines.append(line)

    # Flush any remaining content
    flush_block()

    return blocks


def _match_images_to_blocks(
    blocks: list[dict[str, Any]],
    images: list[ProcessedImage],
) -> list[dict[str, Any]]:
    """Match processed images to relevant blocks.

    Uses slide index proximity and content matching to associate
    images with blocks where they should appear.

    Args:
        blocks: Parsed content blocks
        images: Processed images with transcriptions/descriptions

    Returns:
        Blocks with matched images added
    """
    if not images:
        return blocks

    # Group images by slide index for easy lookup
    images_by_slide: dict[int, list[ProcessedImage]] = {}
    for img in images:
        if img.slide_index not in images_by_slide:
            images_by_slide[img.slide_index] = []
        images_by_slide[img.slide_index].append(img)

    # For each block, find relevant images
    # This is a heuristic - we can improve it later
    for block in blocks:
        block["images"] = []

    # Distribute images across blocks
    # Simple approach: assign images to blocks proportionally by position
    if blocks:
        total_blocks = len(blocks)
        for slide_idx, slide_images in images_by_slide.items():
            # Estimate which block this slide corresponds to
            # (This is a rough heuristic)
            block_idx = min(slide_idx, total_blocks - 1)
            if 0 <= block_idx < len(blocks):
                blocks[block_idx]["images"].extend(slide_images)

    return blocks


def _create_markdown_blocks(
    blocks: list[dict[str, Any]],
    chapter_outline: ChapterOutline,
) -> list[MarkdownBlock]:
    """Convert parsed blocks to MarkdownBlock objects.

    Args:
        blocks: Parsed content blocks with matched images
        chapter_outline: Chapter structure

    Returns:
        List of MarkdownBlock objects ready for card generation
    """
    markdown_blocks: list[MarkdownBlock] = []

    for i, block in enumerate(blocks):
        content = block["content"]
        block_type = block["type"]
        chapter: Chapter | None = block.get("chapter")
        images: list[ProcessedImage] = block.get("images", [])

        # Add image content to block
        for img in images:
            img_markdown = img.to_markdown()
            if img_markdown:
                content = f"{content}\n\n{img_markdown}"

        # Determine kind based on block type
        kind = block_type
        if block_type == "paragraph":
            kind = "fact"  # Default for general content

        # Create evidence reference
        chapter_title = chapter.title if chapter else chapter_outline.document_name
        evidence = Evidence(
            document_id=None,
            slide_index=i,  # Use block index as proxy
            bbox=None,
            text_snippet=content[:100] if len(content) > 100 else content,
        )

        # Generate stable anchor ID
        anchor_id = content_hash(f"{kind}:{content}")[:12]

        markdown_block = MarkdownBlock(
            anchor_id=anchor_id,
            kind=kind,
            content=content,
            evidence=[evidence],
            position_index=i,
            chapter_title=chapter_title,
        )
        markdown_blocks.append(markdown_block)

    return markdown_blocks


def _render_final_markdown(
    markdown_blocks: list[MarkdownBlock],
    chapter_outline: ChapterOutline,
) -> str:
    """Render the final markdown document from blocks.

    Args:
        markdown_blocks: List of processed MarkdownBlock objects
        chapter_outline: Chapter structure for organization

    Returns:
        Complete markdown document string
    """
    lines: list[str] = []

    # Document title
    lines.append(f"# {chapter_outline.document_name}")
    lines.append("")

    # Group blocks by chapter
    chapter_blocks: dict[str, list[MarkdownBlock]] = {}
    for block in markdown_blocks:
        chapter = block.chapter_title
        if chapter not in chapter_blocks:
            chapter_blocks[chapter] = []
        chapter_blocks[chapter].append(block)

    # Render each chapter
    for chapter in chapter_outline.chapters:
        blocks = chapter_blocks.get(chapter.title, [])
        if not blocks:
            continue

        lines.append(f"## {chapter.title}")
        lines.append("")

        for block in blocks:
            # Add anchor comment for tracking
            lines.append(f"<!-- block:{block.anchor_id} -->")
            lines.append(block.content)
            lines.append("")

    # Handle any blocks not assigned to chapters
    default_title = chapter_outline.document_name
    if default_title in chapter_blocks:
        remaining = chapter_blocks[default_title]
        if remaining and (
            len(chapter_outline.chapters) == 0
            or len(chapter_blocks) > len(chapter_outline.chapters)
        ):
            for block in remaining:
                lines.append(f"<!-- block:{block.anchor_id} -->")
                lines.append(block.content)
                lines.append("")

    return "\n".join(lines).strip() + "\n"


def create_assemble_markdown_node(
    config: HolisticConfig | None = None,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create the markdown assembly node for the holistic pipeline.

    This node combines organized markdown content with processed images
    to create the final document and MarkdownBlock objects for card generation.

    Args:
        config: Holistic processing configuration

    Returns:
        Node function for the LangGraph pipeline
    """
    resolved_config = config or HolisticConfig()

    def assemble_markdown_node(state: dict[str, Any]) -> dict[str, Any]:
        """Assemble the final markdown document.

        Args:
            state: Pipeline state with organized_markdown, processed_images, chapter_outline

        Returns:
            Updated state with markdown_blocks, markdown_content
        """
        organized_markdown: str = state.get("organized_markdown", "")
        processed_images: list[ProcessedImage] = state.get("processed_images", [])
        chapter_outline: ChapterOutline | None = state.get("chapter_outline")
        document = state.get("document")

        if not organized_markdown:
            logger.warning("No organized markdown for assembly")
            return {
                **state,
                "markdown_blocks": [],
                "markdown_content": "",
                "current_step": "assemble_markdown",
                "progress": 60,
            }

        # Create default chapter outline if none exists
        if not chapter_outline:
            document_name = document.name if document else "Document"
            slides = state.get("slides", [])
            chapter_outline = ChapterOutline(
                document_name=document_name,
                chapters=[],
                total_slides=len(slides),
            )

        # Parse markdown into blocks
        blocks = _parse_markdown_to_blocks(organized_markdown, chapter_outline)
        logger.info(f"Parsed {len(blocks)} content blocks")

        # Match images to blocks
        if processed_images and resolved_config.embed_complex_images:
            blocks = _match_images_to_blocks(blocks, processed_images)
            logger.info(f"Matched {len(processed_images)} images to blocks")

        # Create MarkdownBlock objects
        markdown_blocks = _create_markdown_blocks(blocks, chapter_outline)
        logger.info(f"Created {len(markdown_blocks)} markdown blocks")

        # Render final document
        markdown_content = _render_final_markdown(markdown_blocks, chapter_outline)

        return {
            **state,
            "markdown_blocks": markdown_blocks,
            "markdown_content": markdown_content,
            "current_step": "assemble_markdown",
            "progress": 60,
        }

    return assemble_markdown_node
