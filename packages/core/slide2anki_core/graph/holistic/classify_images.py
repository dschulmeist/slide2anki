"""Image classification node for the holistic pipeline.

This module classifies extracted images into categories that determine
how they should be processed:

- FORMULA: Mathematical equations -> transcribe to LaTeX
- DIAGRAM: Flowcharts, architectures -> describe + optionally embed
- CHART: Data visualizations -> describe the data/trends
- CODE: Code screenshots -> transcribe to code blocks
- TABLE: Data tables -> transcribe to markdown tables
- PHOTO: Real photographs -> describe + embed if relevant
- LOGO: Branding elements -> skip (should be filtered earlier)
- DECORATIVE: Generic illustrations -> skip
- UNKNOWN: Can't determine -> manual review

The classification uses a vision model with a specialized prompt to
quickly categorize images before more expensive transcription/description.
"""

import asyncio
from collections.abc import Callable
from typing import Any

from slide2anki_core.graph.config import HolisticConfig
from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.images import ExtractedImage, ImageType, ProcessedImage
from slide2anki_core.utils.logging import get_logger

logger = get_logger(__name__)

CLASSIFY_IMAGE_PROMPT = """Classify this image into exactly ONE of these categories:

1. FORMULA - Mathematical equation, formula, or mathematical notation
2. DIAGRAM - Flowchart, architecture diagram, pipeline, process flow, block diagram
3. CHART - Graph, plot, data visualization, bar chart, line chart, pie chart
4. CODE - Screenshot of source code or terminal output
5. TABLE - Data table with rows and columns
6. PHOTO - Real-world photograph (people, objects, places)
7. LOGO - Company logo, university logo, brand mark
8. DECORATIVE - Generic illustration, icon, stock image, clipart

Respond with a JSON object:
{
  "type": "<one of: formula, diagram, chart, code, table, photo, logo, decorative>",
  "confidence": <0.0-1.0>,
  "reason": "<brief explanation>"
}

Be precise. If it contains mathematical notation, it's likely FORMULA.
If it shows data relationships or flows, it's likely DIAGRAM.
If it shows numerical data visually, it's likely CHART.
"""


def _parse_classification_response(
    response: dict[str, Any] | list[dict[str, Any]],
) -> tuple[ImageType, float, str]:
    """Parse the classification response from the model.

    Args:
        response: Parsed JSON response from the model

    Returns:
        Tuple of (ImageType, confidence, reason)
    """
    if isinstance(response, list):
        response = response[0] if response else {}

    type_str = response.get("type", "unknown").lower().strip()
    confidence = float(response.get("confidence", 0.5))
    reason = response.get("reason", "")

    # Map string to ImageType enum
    type_mapping = {
        "formula": ImageType.FORMULA,
        "diagram": ImageType.DIAGRAM,
        "chart": ImageType.CHART,
        "code": ImageType.CODE,
        "table": ImageType.TABLE,
        "photo": ImageType.PHOTO,
        "logo": ImageType.LOGO,
        "decorative": ImageType.DECORATIVE,
    }

    image_type = type_mapping.get(type_str, ImageType.UNKNOWN)
    return image_type, confidence, reason


async def _classify_single_image(
    adapter: BaseModelAdapter,
    image: ExtractedImage,
) -> ProcessedImage:
    """Classify a single image using the vision model.

    Args:
        adapter: Model adapter for vision calls
        image: Extracted image to classify

    Returns:
        ProcessedImage with classification results
    """
    try:
        response = await adapter.generate_structured(
            prompt=CLASSIFY_IMAGE_PROMPT,
            image_data=image.image_data,
        )
        image_type, confidence, reason = _parse_classification_response(response)

        logger.debug(
            f"Classified image {image.image_id} as {image_type.value} "
            f"(confidence={confidence:.2f}, reason={reason})"
        )

    except Exception as e:
        logger.warning(f"Failed to classify image {image.image_id}: {e}")
        image_type = ImageType.UNKNOWN
        confidence = 0.0

    # Determine if we should embed the original image
    # Embed diagrams, charts, and photos; don't embed formulas/code/tables (transcribed)
    should_embed = image_type in (
        ImageType.DIAGRAM,
        ImageType.CHART,
        ImageType.PHOTO,
    )

    return ProcessedImage(
        image_id=image.image_id,
        slide_index=image.slide_index,
        image_type=image_type,
        position=image.position,
        transcription=None,  # Will be filled by transcribe node
        description=None,  # Will be filled by transcribe node
        should_embed=should_embed,
        image_data=image.image_data if should_embed else None,
        confidence=confidence,
    )


async def _classify_images_batch(
    adapter: BaseModelAdapter,
    images: list[ExtractedImage],
    max_concurrent: int = 5,
) -> list[ProcessedImage]:
    """Classify a batch of images with concurrency control.

    Args:
        adapter: Model adapter for vision calls
        images: List of extracted images to classify
        max_concurrent: Maximum concurrent classification calls

    Returns:
        List of ProcessedImage with classification results
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def classify_with_semaphore(image: ExtractedImage) -> ProcessedImage:
        async with semaphore:
            return await _classify_single_image(adapter, image)

    tasks = [classify_with_semaphore(img) for img in images]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed: list[ProcessedImage] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(
                f"Classification failed for image {images[i].image_id}: {result}"
            )
            # Create unknown classification for failed images
            processed.append(
                ProcessedImage(
                    image_id=images[i].image_id,
                    slide_index=images[i].slide_index,
                    image_type=ImageType.UNKNOWN,
                    position=images[i].position,
                    should_embed=False,
                    confidence=0.0,
                )
            )
        else:
            processed.append(result)

    return processed


def create_classify_images_node(
    adapter: BaseModelAdapter,
    config: HolisticConfig | None = None,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create an image classification node for the holistic pipeline.

    This node classifies each extracted image into categories that determine
    how it should be processed (transcribed, described, or skipped).

    Args:
        adapter: Model adapter for vision calls
        config: Holistic processing configuration

    Returns:
        Async node function for the LangGraph pipeline
    """
    # Config is available for future use (e.g., filtering by type)
    _ = config or HolisticConfig()

    async def classify_images_node(state: dict[str, Any]) -> dict[str, Any]:
        """Classify extracted images by type.

        Args:
            state: Pipeline state with extracted_images

        Returns:
            Updated state with classified_images list
        """
        extracted_images: list[ExtractedImage] = state.get("extracted_images", [])

        if not extracted_images:
            logger.info("No images to classify")
            return {
                **state,
                "classified_images": [],
                "current_step": "classify_images",
                "progress": 25,
            }

        logger.info(f"Classifying {len(extracted_images)} images")

        classified_images = await _classify_images_batch(
            adapter=adapter,
            images=extracted_images,
            max_concurrent=5,
        )

        # Log classification summary
        type_counts = {}
        for img in classified_images:
            type_counts[img.image_type.value] = (
                type_counts.get(img.image_type.value, 0) + 1
            )

        logger.info(f"Classification results: {type_counts}")

        # Filter out logos and decorative images
        content_images = [
            img
            for img in classified_images
            if img.image_type not in (ImageType.LOGO, ImageType.DECORATIVE)
        ]

        logger.info(
            f"Filtered to {len(content_images)} content images "
            f"(removed {len(classified_images) - len(content_images)} logos/decorative)"
        )

        return {
            **state,
            "classified_images": content_images,
            "current_step": "classify_images",
            "progress": 25,
        }

    return classify_images_node
