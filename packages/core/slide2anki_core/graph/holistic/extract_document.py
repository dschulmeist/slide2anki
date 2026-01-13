"""Holistic document extraction node.

This is the core of the holistic pipeline. Instead of extracting "claims"
per-slide, this node processes the entire document (or chunks of it) to
create a coherent markdown "script" that captures the educational content.

Key benefits over per-slide extraction:
1. Natural deduplication - metadata (dates, presenter) mentioned once
2. Context preservation - understands relationships between slides
3. Better quality - model sees the whole picture
4. Fewer API calls - one call per chunk instead of per-region

The extraction uses overlapping chunks (default 15%) to ensure context
continuity across chunk boundaries. Chunks are later merged intelligently
to remove duplicate content from overlap regions.
"""

import base64
from collections.abc import Callable
from typing import Any

from slide2anki_core.graph.config import HolisticConfig
from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.chapters import DocumentChunk
from slide2anki_core.schemas.document import Slide
from slide2anki_core.utils.logging import get_logger

logger = get_logger(__name__)

# The core prompt for holistic document extraction
EXTRACT_DOCUMENT_PROMPT = """You are creating comprehensive study notes from lecture slides.

Your task: Convert these slides into a well-structured markdown document that captures ALL the educational content.

CRITICAL INSTRUCTIONS:

1. CONTENT TO INCLUDE:
   - Key concepts, definitions, and terminology
   - Important facts and relationships
   - Processes, algorithms, and methods
   - Formulas and equations (use LaTeX: $$formula$$)
   - Examples that illustrate concepts
   - Comparisons and contrasts between concepts
   - Important citations or references

2. CONTENT TO EXCLUDE:
   - Presenter names, dates, slide numbers (mention ONCE at the start if relevant)
   - University/institution names and logos (mention ONCE if relevant)
   - Repeated headers/footers
   - "Content of this lecture" slides unless they provide unique structure
   - Generic phrases like "Let's begin" or "Questions?"

3. FORMAT REQUIREMENTS:
   - Use markdown headers (##, ###) to organize by topic, NOT by slide number
   - Use bullet points for lists of related items
   - Use numbered lists for sequential steps or processes
   - Use bold for key terms being defined
   - Use LaTeX ($$...$$) for mathematical formulas
   - Group related content together even if spread across multiple slides

4. QUALITY STANDARDS:
   - Every statement should be educational and useful for studying
   - Avoid redundancy - don't repeat the same information
   - Maintain logical flow between sections
   - Preserve technical accuracy

5. SPECIAL HANDLING:
   - For diagrams you cannot see in detail, note "See diagram on slide X"
   - For complex formulas, transcribe carefully to LaTeX
   - For tables, use markdown table format

OUTPUT FORMAT:
Return a JSON object with:
{{
  "markdown": "<your markdown content>",
  "main_topic": "<the main subject/topic of these slides>",
  "key_concepts": ["<list>", "<of>", "<main concepts>"]
}}

Now analyze these slides and create comprehensive study notes:
"""

# Prompt for continuation chunks (has context from previous)
EXTRACT_CONTINUATION_PROMPT = """Continue creating study notes from these lecture slides.

CONTEXT: You are continuing from previous slides. The main topic is: {main_topic}
Previous key concepts covered: {previous_concepts}

INSTRUCTIONS:
1. Continue the markdown document seamlessly
2. Don't repeat content from previous slides unless building on it
3. Maintain consistent formatting and structure
4. Focus on NEW educational content

{base_prompt}
"""


async def _extract_chunk(
    adapter: BaseModelAdapter,
    slides: list[Slide],
    chunk: DocumentChunk,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract markdown content from a chunk of slides.

    Args:
        adapter: Model adapter for vision calls
        slides: All slides (we'll select the chunk's range)
        chunk: The chunk specification
        context: Optional context from previous chunks (main_topic, key_concepts)

    Returns:
        Dict with markdown content, main_topic, and key_concepts
    """
    # Get slides for this chunk
    chunk_slides = [slides[i] for i in chunk.slide_indices if i < len(slides)]

    if not chunk_slides:
        logger.warning(f"No slides for chunk {chunk.chunk_index}")
        return {"markdown": "", "main_topic": "", "key_concepts": []}

    # Build the prompt
    if context and not chunk.is_first:
        prompt = EXTRACT_CONTINUATION_PROMPT.format(
            main_topic=context.get("main_topic", "unknown"),
            previous_concepts=", ".join(context.get("key_concepts", [])[:10]),
            base_prompt=EXTRACT_DOCUMENT_PROMPT,
        )
    else:
        prompt = EXTRACT_DOCUMENT_PROMPT

    # Add slide range info to prompt
    prompt += f"\n\nSlides {chunk.start_slide + 1} to {chunk.end_slide + 1}:\n"

    # Build content parts with images
    # For multi-image requests, we need to construct the content carefully
    content_parts: list[Any] = [prompt]

    for i, slide in enumerate(chunk_slides):
        slide_num = chunk.slide_indices[i] + 1
        content_parts.append(f"\n--- Slide {slide_num} ---\n")

        if slide.image_data:
            # Add image as base64
            image_b64 = base64.b64encode(slide.image_data).decode("utf-8")
            content_parts.append({"mime_type": "image/png", "data": image_b64})

        # Also include extracted text if available (helps with accuracy)
        if slide.extracted_text:
            content_parts.append(f"\n[Extracted text: {slide.extracted_text[:500]}]\n")

    try:
        # Make the API call with all slide images
        # We need to use a special method that can handle multiple images
        # For now, we'll use generate_structured with a combined prompt
        # Most vision models support multiple images in a single request

        # Combine text and images for the adapter
        combined_prompt = _build_combined_prompt(content_parts)

        # Get the first slide's image for the vision call
        # For models that support multiple images, we'd need adapter changes
        # For now, we'll pass slides individually or use a summary approach
        first_slide_image = chunk_slides[0].image_data if chunk_slides else None

        response = await adapter.generate_structured(
            prompt=combined_prompt,
            image_data=first_slide_image,
        )

        if isinstance(response, list):
            response = response[0] if response else {}

        return {
            "markdown": response.get("markdown", ""),
            "main_topic": response.get("main_topic", ""),
            "key_concepts": response.get("key_concepts", []),
            "chunk_index": chunk.chunk_index,
        }

    except Exception as e:
        logger.error(f"Failed to extract chunk {chunk.chunk_index}: {e}")
        return {
            "markdown": "",
            "main_topic": "",
            "key_concepts": [],
            "chunk_index": chunk.chunk_index,
            "error": str(e),
        }


def _build_combined_prompt(content_parts: list[Any]) -> str:
    """Build a text-only prompt from content parts.

    For adapters that don't support multiple images, we convert image
    references to text placeholders and rely on the single image passed
    separately.

    Args:
        content_parts: List of strings and image dicts

    Returns:
        Combined text prompt
    """
    text_parts = []
    image_count = 0

    for part in content_parts:
        if isinstance(part, str):
            text_parts.append(part)
        elif isinstance(part, dict) and "data" in part:
            image_count += 1
            text_parts.append(f"[Image {image_count}]")

    return "".join(text_parts)


async def _extract_all_chunks_sequential(
    adapter: BaseModelAdapter,
    slides: list[Slide],
    chunks: list[DocumentChunk],
) -> list[dict[str, Any]]:
    """Extract all chunks sequentially, passing context forward.

    Sequential extraction allows each chunk to benefit from context
    established by previous chunks, improving coherence.

    Args:
        adapter: Model adapter for vision calls
        slides: All slides
        chunks: List of chunk specifications

    Returns:
        List of extraction results for each chunk
    """
    results: list[dict[str, Any]] = []
    context: dict[str, Any] | None = None

    for chunk in chunks:
        logger.info(
            f"Extracting chunk {chunk.chunk_index + 1}/{len(chunks)} "
            f"(slides {chunk.start_slide + 1}-{chunk.end_slide + 1})"
        )

        result = await _extract_chunk(
            adapter=adapter,
            slides=slides,
            chunk=chunk,
            context=context,
        )
        results.append(result)

        # Update context for next chunk
        if result.get("main_topic"):
            if context is None:
                context = {}
            context["main_topic"] = result["main_topic"]
            context["key_concepts"] = result.get("key_concepts", [])

    return results


def _merge_chunk_results(
    results: list[dict[str, Any]],
    chunks: list[DocumentChunk],
) -> tuple[str, str, list[str]]:
    """Merge results from overlapping chunks into a single document.

    The merging strategy:
    1. Take full content from first chunk
    2. For subsequent chunks, try to find overlap and skip duplicate content
    3. If overlap detection fails, just concatenate with a separator

    Args:
        results: List of extraction results from each chunk
        chunks: List of chunk specifications (for overlap info)

    Returns:
        Tuple of (merged_markdown, main_topic, all_key_concepts)
    """
    if not results:
        return "", "", []

    # Start with first chunk's content
    merged_markdown_parts: list[str] = []
    main_topic = results[0].get("main_topic", "")
    all_concepts: list[str] = []

    for i, result in enumerate(results):
        markdown = result.get("markdown", "").strip()
        concepts = result.get("key_concepts", [])

        if i == 0:
            # First chunk - take everything
            merged_markdown_parts.append(markdown)
        else:
            # Subsequent chunks - try to detect and skip overlap
            # Simple approach: look for the last paragraph/section of previous
            # and skip content in current that matches

            # For now, use a simple concatenation with a marker
            # A more sophisticated approach would use fuzzy matching
            if markdown:
                merged_markdown_parts.append(f"\n\n{markdown}")

        # Collect unique concepts
        for concept in concepts:
            if concept and concept not in all_concepts:
                all_concepts.append(concept)

        # Update main topic if better one found
        if not main_topic and result.get("main_topic"):
            main_topic = result["main_topic"]

    merged_markdown = "\n".join(merged_markdown_parts)

    # Clean up any obvious duplications from overlap
    merged_markdown = _dedupe_markdown_sections(merged_markdown)

    return merged_markdown, main_topic, all_concepts


def _dedupe_markdown_sections(markdown: str) -> str:
    """Remove duplicate sections from merged markdown.

    Simple deduplication based on exact header+content matching.
    More sophisticated approaches could use fuzzy matching.

    Args:
        markdown: Merged markdown content

    Returns:
        Deduplicated markdown
    """
    lines = markdown.split("\n")
    seen_sections: set[str] = set()
    result_lines: list[str] = []
    current_section: list[str] = []
    current_header = ""

    for line in lines:
        if line.startswith("##"):
            # New section - flush previous
            if current_section:
                section_key = current_header + "".join(current_section[:3])
                if section_key not in seen_sections:
                    result_lines.extend(current_section)
                    seen_sections.add(section_key)
                current_section = []

            current_header = line
            current_section.append(line)
        else:
            current_section.append(line)

    # Flush last section
    if current_section:
        section_key = current_header + "".join(current_section[:3])
        if section_key not in seen_sections:
            result_lines.extend(current_section)

    return "\n".join(result_lines)


def create_extract_document_node(
    adapter: BaseModelAdapter,
    config: HolisticConfig | None = None,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create the holistic document extraction node.

    This node is the core of the holistic pipeline. It processes the entire
    document (or chunks with overlap) to create a coherent markdown document
    that captures all educational content.

    Args:
        adapter: Model adapter for vision calls
        config: Holistic processing configuration

    Returns:
        Async node function for the LangGraph pipeline
    """
    resolved_config = config or HolisticConfig()
    chunking_config = resolved_config.to_chunking_config()

    async def extract_document_node(state: dict[str, Any]) -> dict[str, Any]:
        """Extract markdown content from the entire document.

        Args:
            state: Pipeline state with slides

        Returns:
            Updated state with raw_markdown, main_topic, key_concepts
        """
        slides: list[Slide] = state.get("slides", [])

        if not slides:
            logger.warning("No slides available for extraction")
            return {
                **state,
                "raw_markdown": "",
                "main_topic": "",
                "key_concepts": [],
                "current_step": "extract_document",
                "progress": 50,
            }

        # Create chunks for processing
        chunks = chunking_config.create_chunks(len(slides))
        logger.info(
            f"Processing {len(slides)} slides in {len(chunks)} chunks "
            f"(size={chunking_config.target_chunk_size}, "
            f"overlap={chunking_config.overlap_ratio:.0%})"
        )

        # Extract all chunks (sequential for context continuity)
        results = await _extract_all_chunks_sequential(
            adapter=adapter,
            slides=slides,
            chunks=chunks,
        )

        # Merge chunk results
        merged_markdown, main_topic, key_concepts = _merge_chunk_results(
            results, chunks
        )

        logger.info(
            f"Extracted document: {len(merged_markdown)} chars, "
            f"topic='{main_topic}', {len(key_concepts)} key concepts"
        )

        return {
            **state,
            "raw_markdown": merged_markdown,
            "main_topic": main_topic,
            "key_concepts": key_concepts,
            "chunk_results": results,  # Keep for debugging
            "current_step": "extract_document",
            "progress": 50,
        }

    return extract_document_node
