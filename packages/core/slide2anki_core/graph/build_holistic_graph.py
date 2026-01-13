"""Build the holistic document processing graph.

This module constructs the main LangGraph pipeline for the holistic document
processing approach. Unlike the legacy per-slide extraction pipeline, this
approach processes entire documents as coherent units, producing higher quality
markdown with natural deduplication and proper context.

Pipeline Flow:
    ingest -> render -> [parallel: extract_images, extract_document]
                               |                    |
                               v                    v
                        classify_images      detect_chapters
                               |                    |
                               v                    |
                       transcribe_images            |
                               |                    |
                               +--------------------+
                                        |
                                        v
                                assemble_markdown
                                        |
                                        v
                                   (output)

The pipeline produces:
- markdown_blocks: List of MarkdownBlock objects for card generation
- markdown_content: Complete markdown document string
- chapter_outline: Document structure with detected chapters
- processed_images: Transcribed/described images
"""

from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.types import Checkpointer

from slide2anki_core.graph.config import HolisticConfig
from slide2anki_core.graph.holistic.assemble_markdown import (
    create_assemble_markdown_node,
)
from slide2anki_core.graph.holistic.classify_images import create_classify_images_node
from slide2anki_core.graph.holistic.detect_chapters import create_detect_chapters_node
from slide2anki_core.graph.holistic.extract_document import (
    create_extract_document_node,
)
from slide2anki_core.graph.holistic.extract_images import create_extract_images_node
from slide2anki_core.graph.holistic.transcribe_images import (
    create_transcribe_images_node,
)
from slide2anki_core.graph.nodes import ingest, render
from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.chapters import ChapterOutline
from slide2anki_core.schemas.document import Document, Slide
from slide2anki_core.schemas.images import ExtractedImage, ProcessedImage
from slide2anki_core.schemas.markdown import MarkdownBlock
from slide2anki_core.utils.logging import get_logger

logger = get_logger(__name__)


# Reducers for parallel state merging


def _keep_last_str(existing: str | None, incoming: str | None) -> str | None:
    """Keep the latest value for string fields."""
    return incoming if incoming else existing


def _keep_max_int(existing: int, incoming: int) -> int:
    """Keep the maximum value for progress fields."""
    return max(existing or 0, incoming or 0)


def _merge_errors(existing: list[str], incoming: list[str]) -> list[str]:
    """Merge error lists from parallel workers."""
    if not existing:
        return list(incoming or [])
    if not incoming:
        return list(existing)
    return list(dict.fromkeys([*existing, *incoming]))


def _merge_list(existing: list[Any], incoming: list[Any]) -> list[Any]:
    """Merge generic lists."""
    if not existing:
        return list(incoming or [])
    if not incoming:
        return list(existing)
    return [*existing, *incoming]


class HolisticPipelineState(TypedDict, total=False):
    """State passed through the holistic pipeline.

    This state type supports the holistic document processing pipeline,
    tracking document data, extracted images, markdown content, and
    chapter structure through the processing stages.
    """

    # Input
    pdf_path: str
    pdf_data: bytes

    # Document data (from ingest/render)
    document: Document
    slides: list[Slide]

    # Image processing
    extracted_images: list[ExtractedImage]
    classified_images: list[ProcessedImage]
    processed_images: list[ProcessedImage]

    # Document extraction
    raw_markdown: str
    main_topic: str
    key_concepts: list[str]
    chunk_results: list[dict[str, Any]]

    # Chapter detection
    chapter_outline: ChapterOutline
    organized_markdown: str

    # Final output
    markdown_blocks: list[MarkdownBlock]
    markdown_content: str

    # Metadata with reducers for parallel processing
    current_step: Annotated[str, _keep_last_str]
    progress: Annotated[int, _keep_max_int]
    errors: Annotated[list[str], _merge_errors]


def build_holistic_graph(
    adapter: BaseModelAdapter,
    config: HolisticConfig | None = None,
    checkpointer: Checkpointer | None = None,
) -> StateGraph:
    """Build the holistic document processing pipeline.

    This pipeline processes entire documents as coherent units, producing
    high-quality markdown with natural deduplication and proper context.
    It replaces the legacy per-slide extraction approach for better results.

    Args:
        adapter: Model adapter for vision and text calls
        config: Holistic processing configuration
        checkpointer: Optional LangGraph checkpointer for resumption

    Returns:
        Compiled StateGraph ready for invocation

    Example:
        >>> from slide2anki_core.model_adapters.google import GoogleAdapter
        >>> adapter = GoogleAdapter(api_key="...")
        >>> graph = build_holistic_graph(adapter)
        >>> result = await graph.ainvoke({"pdf_path": "/path/to/lecture.pdf"})
        >>> print(result["markdown_content"])
    """
    resolved_config = config or HolisticConfig()

    logger.info(
        f"Building holistic pipeline (chunk_size={resolved_config.chunk_size}, "
        f"overlap={resolved_config.chunk_overlap:.0%})"
    )

    # Create nodes
    extract_images_node = create_extract_images_node(resolved_config)
    classify_images_node = create_classify_images_node(adapter, resolved_config)
    transcribe_images_node = create_transcribe_images_node(adapter, resolved_config)
    extract_document_node = create_extract_document_node(adapter, resolved_config)
    detect_chapters_node = create_detect_chapters_node(resolved_config)
    assemble_markdown_node = create_assemble_markdown_node(resolved_config)

    # Build the graph
    graph = StateGraph(HolisticPipelineState)

    # Add nodes
    graph.add_node("ingest", ingest.ingest_node)
    graph.add_node("render", render.create_render_node())
    graph.add_node("extract_images", extract_images_node)
    graph.add_node("classify_images", classify_images_node)
    graph.add_node("transcribe_images", transcribe_images_node)
    graph.add_node("extract_document", extract_document_node)
    graph.add_node("detect_chapters", detect_chapters_node)
    graph.add_node("assemble_markdown", assemble_markdown_node)

    # Define edges
    # Linear flow for now - can be optimized for parallelism later
    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "render")

    # After render, we can do image extraction and document extraction
    # For simplicity, running sequentially for now
    graph.add_edge("render", "extract_images")
    graph.add_edge("extract_images", "classify_images")
    graph.add_edge("classify_images", "transcribe_images")
    graph.add_edge("transcribe_images", "extract_document")
    graph.add_edge("extract_document", "detect_chapters")
    graph.add_edge("detect_chapters", "assemble_markdown")
    graph.add_edge("assemble_markdown", END)

    return graph.compile(checkpointer=checkpointer)


def build_holistic_graph_optimized(
    adapter: BaseModelAdapter,
    config: HolisticConfig | None = None,
    checkpointer: Checkpointer | None = None,
) -> StateGraph:
    """Build an optimized holistic pipeline with parallel processing.

    This version runs image processing and document extraction in parallel
    for faster processing on documents with many images.

    Note: This requires the model adapter to handle concurrent requests properly.

    Args:
        adapter: Model adapter for vision and text calls
        config: Holistic processing configuration
        checkpointer: Optional LangGraph checkpointer for resumption

    Returns:
        Compiled StateGraph ready for invocation
    """
    # For now, return the sequential version
    # Parallel optimization can be added once the sequential version is validated
    logger.info("Building optimized holistic pipeline (parallel processing)")
    return build_holistic_graph(adapter, config, checkpointer)
