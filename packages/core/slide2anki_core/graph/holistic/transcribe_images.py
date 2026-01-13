"""Image transcription and description node for the holistic pipeline.

This module processes classified images based on their type:

- FORMULA: Transcribe to LaTeX notation
- CODE: Transcribe to source code text
- TABLE: Transcribe to markdown table format
- DIAGRAM: Generate descriptive text explaining the diagram
- CHART: Generate description of what the data shows
- PHOTO: Generate description if relevant to content

Each image type has a specialized prompt optimized for that content.
The results are stored in ProcessedImage.transcription or .description
fields for later embedding in the markdown document.
"""

import asyncio
from collections.abc import Callable
from typing import Any

from slide2anki_core.graph.config import HolisticConfig
from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.images import ImageType, ProcessedImage
from slide2anki_core.utils.logging import get_logger

logger = get_logger(__name__)

# Specialized prompts for each image type

TRANSCRIBE_FORMULA_PROMPT = """Transcribe this mathematical formula/equation to LaTeX.

Rules:
1. Output ONLY the LaTeX code, no explanation
2. Use standard LaTeX math notation
3. Do NOT include surrounding $ or $$ delimiters
4. Preserve the exact mathematical meaning
5. Use \\frac{}{} for fractions, ^{} for superscripts, _{} for subscripts

Example output: E = mc^2
Example output: \\frac{\\partial f}{\\partial x} = \\lim_{h \\to 0} \\frac{f(x+h) - f(x)}{h}

Respond with JSON:
{"latex": "<your LaTeX transcription>"}
"""

TRANSCRIBE_CODE_PROMPT = """Transcribe this code screenshot to text.

Rules:
1. Output the exact code as shown in the image
2. Preserve indentation and formatting
3. Include comments if visible
4. If you can identify the programming language, note it

Respond with JSON:
{
  "code": "<the transcribed code>",
  "language": "<detected language or 'unknown'>"
}
"""

TRANSCRIBE_TABLE_PROMPT = """Transcribe this table to markdown format.

Rules:
1. Use standard markdown table syntax with | separators
2. Include header row with --- separator
3. Preserve all data and column alignment
4. If cells are empty, leave them empty in markdown

Example output:
| Column1 | Column2 | Column3 |
|---------|---------|---------|
| data1   | data2   | data3   |

Respond with JSON:
{"markdown": "<your markdown table>"}
"""

DESCRIBE_DIAGRAM_PROMPT = """Describe this diagram in detail for someone who cannot see it.

Focus on:
1. What type of diagram is this (flowchart, architecture, process, etc.)?
2. What are the main components/elements?
3. How do the elements connect/relate to each other?
4. What is the overall meaning or purpose?

Be concise but complete. Use plain language.

Respond with JSON:
{"description": "<your description>"}
"""

DESCRIBE_CHART_PROMPT = """Describe what this chart/graph shows.

Focus on:
1. What type of chart is this (bar, line, pie, scatter, etc.)?
2. What variables are being compared/shown?
3. What are the key trends or patterns?
4. What conclusions can be drawn?

Be concise but informative. Focus on the data insights.

Respond with JSON:
{"description": "<your description>"}
"""

DESCRIBE_PHOTO_PROMPT = """Briefly describe this image and its relevance to educational content.

Focus on:
1. What does the image show?
2. Why might it be included in educational material?
3. What concept or idea does it illustrate?

Be concise - 1-2 sentences.

Respond with JSON:
{"description": "<your description>"}
"""


def _get_prompt_for_type(image_type: ImageType) -> str | None:
    """Get the appropriate prompt for an image type.

    Args:
        image_type: The classified image type

    Returns:
        Prompt string, or None if no processing needed
    """
    prompts = {
        ImageType.FORMULA: TRANSCRIBE_FORMULA_PROMPT,
        ImageType.CODE: TRANSCRIBE_CODE_PROMPT,
        ImageType.TABLE: TRANSCRIBE_TABLE_PROMPT,
        ImageType.DIAGRAM: DESCRIBE_DIAGRAM_PROMPT,
        ImageType.CHART: DESCRIBE_CHART_PROMPT,
        ImageType.PHOTO: DESCRIBE_PHOTO_PROMPT,
    }
    return prompts.get(image_type)


def _parse_transcription_response(
    image_type: ImageType,
    response: dict[str, Any] | list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    """Parse the transcription/description response.

    Args:
        image_type: The image type that was processed
        response: Parsed JSON response from the model

    Returns:
        Tuple of (transcription, description) - one will be populated
    """
    if isinstance(response, list):
        response = response[0] if response else {}

    if image_type == ImageType.FORMULA:
        latex = response.get("latex", "").strip()
        return latex if latex else None, None

    if image_type == ImageType.CODE:
        code = response.get("code", "").strip()
        language = response.get("language", "").strip()
        if code:
            # Format as markdown code block content (without fences)
            if language and language != "unknown":
                return f"```{language}\n{code}\n```", None
            return f"```\n{code}\n```", None
        return None, None

    if image_type == ImageType.TABLE:
        markdown = response.get("markdown", "").strip()
        return markdown if markdown else None, None

    if image_type in (ImageType.DIAGRAM, ImageType.CHART, ImageType.PHOTO):
        description = response.get("description", "").strip()
        return None, description if description else None

    return None, None


async def _process_single_image(
    adapter: BaseModelAdapter,
    image: ProcessedImage,
    config: HolisticConfig,
) -> ProcessedImage:
    """Process a single image based on its type.

    Args:
        adapter: Model adapter for vision/text calls
        image: Classified image to process
        config: Holistic processing configuration

    Returns:
        Updated ProcessedImage with transcription/description
    """
    # Check if we should process this type
    if image.image_type == ImageType.FORMULA and not config.transcribe_formulas:
        logger.debug(f"Skipping formula transcription for {image.image_id}")
        return image

    if image.image_type in (ImageType.DIAGRAM, ImageType.CHART, ImageType.PHOTO):
        if not config.describe_diagrams:
            logger.debug(f"Skipping description for {image.image_id}")
            return image

    prompt = _get_prompt_for_type(image.image_type)
    if not prompt:
        logger.debug(f"No processing needed for {image.image_id} ({image.image_type})")
        return image

    try:
        # Get image data for vision call
        image_data = image.image_data
        if not image_data:
            logger.warning(f"No image data for {image.image_id}")
            return image

        response = await adapter.generate_structured(
            prompt=prompt,
            image_data=image_data,
        )

        transcription, description = _parse_transcription_response(
            image.image_type, response
        )

        # Create updated image with results
        return ProcessedImage(
            image_id=image.image_id,
            slide_index=image.slide_index,
            image_type=image.image_type,
            position=image.position,
            transcription=transcription,
            description=description,
            should_embed=image.should_embed,
            image_data=image.image_data if image.should_embed else None,
            confidence=image.confidence,
        )

    except Exception as e:
        logger.error(f"Failed to process image {image.image_id}: {e}")
        return image


async def _process_images_batch(
    adapter: BaseModelAdapter,
    images: list[ProcessedImage],
    config: HolisticConfig,
    max_concurrent: int = 5,
) -> list[ProcessedImage]:
    """Process a batch of images with concurrency control.

    Args:
        adapter: Model adapter for vision calls
        images: List of classified images to process
        config: Holistic processing configuration
        max_concurrent: Maximum concurrent processing calls

    Returns:
        List of ProcessedImage with transcription/description filled
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_with_semaphore(image: ProcessedImage) -> ProcessedImage:
        async with semaphore:
            return await _process_single_image(adapter, image, config)

    tasks = [process_with_semaphore(img) for img in images]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed: list[ProcessedImage] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Processing failed for {images[i].image_id}: {result}")
            processed.append(images[i])  # Keep original
        else:
            processed.append(result)

    return processed


def create_transcribe_images_node(
    adapter: BaseModelAdapter,
    config: HolisticConfig | None = None,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create an image transcription/description node for the holistic pipeline.

    This node processes classified images:
    - Transcribes formulas to LaTeX
    - Transcribes code to code blocks
    - Transcribes tables to markdown
    - Generates descriptions for diagrams, charts, photos

    Args:
        adapter: Model adapter for vision calls
        config: Holistic processing configuration

    Returns:
        Async node function for the LangGraph pipeline
    """
    resolved_config = config or HolisticConfig()

    async def transcribe_images_node(state: dict[str, Any]) -> dict[str, Any]:
        """Transcribe and describe classified images.

        Args:
            state: Pipeline state with classified_images

        Returns:
            Updated state with processed_images list
        """
        classified_images: list[ProcessedImage] = state.get("classified_images", [])

        if not classified_images:
            logger.info("No images to transcribe/describe")
            return {
                **state,
                "processed_images": [],
                "current_step": "transcribe_images",
                "progress": 30,
            }

        # Filter to only images that need processing
        needs_processing = [
            img
            for img in classified_images
            if img.image_type
            in (
                ImageType.FORMULA,
                ImageType.CODE,
                ImageType.TABLE,
                ImageType.DIAGRAM,
                ImageType.CHART,
                ImageType.PHOTO,
            )
        ]

        logger.info(
            f"Processing {len(needs_processing)} images "
            f"(formulas, code, tables, diagrams, charts, photos)"
        )

        processed_images = await _process_images_batch(
            adapter=adapter,
            images=needs_processing,
            config=resolved_config,
            max_concurrent=5,
        )

        # Log processing summary
        transcribed = sum(1 for img in processed_images if img.transcription)
        described = sum(1 for img in processed_images if img.description)
        logger.info(
            f"Processed {len(processed_images)} images: "
            f"{transcribed} transcribed, {described} described"
        )

        return {
            **state,
            "processed_images": processed_images,
            "current_step": "transcribe_images",
            "progress": 30,
        }

    return transcribe_images_node
