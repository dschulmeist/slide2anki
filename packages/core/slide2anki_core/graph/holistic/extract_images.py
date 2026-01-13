"""Image extraction node for the holistic pipeline.

This module extracts images from PDF slides and filters them based on position,
size, and repetition patterns. The goal is to identify meaningful content images
(formulas, diagrams, charts) while filtering out branding elements (logos,
headers, footers) that appear repeatedly across slides.

Filtering strategy:
1. Position-based: Skip images in header (top 15%) and footer (bottom 15%) regions
2. Size-based: Skip images smaller than 5% of slide area (icons, bullets)
3. Repetition-based: Skip images appearing on >50% of slides (logos, branding)
"""

import hashlib
from collections.abc import Callable
from io import BytesIO
from typing import Any

from slide2anki_core.graph.config import HolisticConfig
from slide2anki_core.schemas.document import Slide
from slide2anki_core.schemas.images import ExtractedImage, ImagePosition
from slide2anki_core.utils.logging import get_logger

logger = get_logger(__name__)


def _compute_image_hash(image_data: bytes) -> str:
    """Compute a hash for image data to detect duplicates.

    Uses a perceptual-like approach: hash the raw bytes. For exact duplicates
    (same logo on every slide), this works well. For slightly different images
    (resized logos), we might miss some, but that's acceptable.

    Args:
        image_data: Raw image bytes

    Returns:
        Hex digest of the image hash
    """
    return hashlib.sha256(image_data).hexdigest()[:16]


def _extract_images_from_pdf(
    pdf_data: bytes,
) -> list[tuple[int, dict[str, Any], bytes | None]]:
    """Extract all images from a PDF with their positions.

    Uses pdfplumber to extract images and their bounding boxes from each page.
    Returns tuples of (page_index, image_info_dict, image_bytes).

    Args:
        pdf_data: Raw PDF bytes

    Returns:
        List of (page_index, image_info, image_bytes) tuples
    """
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not installed, cannot extract images")
        return []

    results: list[tuple[int, dict[str, Any], bytes | None]] = []

    try:
        with pdfplumber.open(BytesIO(pdf_data)) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                page_width = page.width
                page_height = page.height

                images = page.images or []
                for img_info in images:
                    # Extract position information
                    x0 = img_info.get("x0", 0)
                    y0 = img_info.get("top", 0)
                    x1 = img_info.get("x1", 0)
                    y1 = img_info.get("bottom", 0)

                    # Normalize to 0-1 coordinates
                    normalized_info = {
                        "x": x0 / page_width if page_width > 0 else 0,
                        "y": y0 / page_height if page_height > 0 else 0,
                        "width": (x1 - x0) / page_width if page_width > 0 else 0,
                        "height": (y1 - y0) / page_height if page_height > 0 else 0,
                        "page_width": page_width,
                        "page_height": page_height,
                    }

                    # Try to extract image bytes
                    # pdfplumber stores image data in the 'stream' attribute
                    image_bytes = None
                    if "stream" in img_info:
                        try:
                            stream = img_info["stream"]
                            if hasattr(stream, "get_data"):
                                image_bytes = stream.get_data()
                            elif isinstance(stream, bytes):
                                image_bytes = stream
                        except Exception as e:
                            logger.debug(f"Could not extract image stream: {e}")

                    results.append((page_idx, normalized_info, image_bytes))

    except Exception as e:
        logger.error(f"Failed to extract images from PDF: {e}")
        return []

    return results


def _extract_images_from_slides(
    slides: list[Slide],
    pdf_data: bytes | None,
    config: HolisticConfig,
) -> list[ExtractedImage]:
    """Extract and filter images from slides.

    This function combines PDF-based image extraction with position-based
    filtering. Images are filtered based on:
    - Position (skip header/footer regions)
    - Size (skip tiny images like icons)

    Args:
        slides: List of rendered slides
        pdf_data: Raw PDF bytes for image extraction
        config: Holistic processing configuration

    Returns:
        List of extracted images that passed initial filtering
    """
    if not pdf_data:
        logger.warning("No PDF data available for image extraction")
        return []

    # Extract raw images from PDF
    raw_images = _extract_images_from_pdf(pdf_data)
    logger.info(f"Extracted {len(raw_images)} raw images from PDF")

    # Track image hashes for repetition detection
    hash_to_images: dict[str, list[ExtractedImage]] = {}
    image_id_counter = 0

    for page_idx, img_info, img_bytes in raw_images:
        # Create position object
        position = ImagePosition(
            x=img_info["x"],
            y=img_info["y"],
            width=img_info["width"],
            height=img_info["height"],
        )

        # Position-based filtering
        if position.is_in_header(config.header_threshold):
            logger.debug(f"Skipping header image on slide {page_idx}")
            continue

        if position.is_in_footer(config.footer_threshold):
            logger.debug(f"Skipping footer image on slide {page_idx}")
            continue

        # Size-based filtering
        if position.area < config.min_image_area:
            logger.debug(
                f"Skipping small image on slide {page_idx} "
                f"(area={position.area:.2%} < {config.min_image_area:.2%})"
            )
            continue

        # If we don't have image bytes, try to crop from rendered slide
        if img_bytes is None and page_idx < len(slides):
            slide = slides[page_idx]
            if slide.image_data:
                img_bytes = _crop_region_from_slide(slide.image_data, position)

        if img_bytes is None:
            logger.debug(f"Skipping image on slide {page_idx}: no image data")
            continue

        # Create extracted image
        image_id = f"img_{image_id_counter:04d}"
        image_id_counter += 1

        extracted = ExtractedImage(
            image_id=image_id,
            slide_index=page_idx,
            position=position,
            image_data=img_bytes,
            occurrence_count=1,
        )

        # Track by hash for repetition detection
        img_hash = _compute_image_hash(img_bytes)
        if img_hash not in hash_to_images:
            hash_to_images[img_hash] = []
        hash_to_images[img_hash].append(extracted)

    # Repetition-based filtering
    # Count how many unique slides each hash appears on
    total_slides = len(slides)
    filtered_images: list[ExtractedImage] = []

    for img_hash, images in hash_to_images.items():
        unique_slides = len(set(img.slide_index for img in images))
        repetition_ratio = unique_slides / total_slides if total_slides > 0 else 0

        if repetition_ratio > config.repetition_threshold:
            logger.info(
                f"Skipping repeated image (hash={img_hash[:8]}..., "
                f"appears on {unique_slides}/{total_slides} slides = "
                f"{repetition_ratio:.0%})"
            )
            continue

        # Update occurrence count and add to results
        for img in images:
            img.occurrence_count = len(images)
            filtered_images.append(img)

    logger.info(
        f"Filtered to {len(filtered_images)} content images "
        f"(removed {len(raw_images) - len(filtered_images)} branding/small images)"
    )

    return filtered_images


def _crop_region_from_slide(image_data: bytes, position: ImagePosition) -> bytes | None:
    """Crop a region from a slide image based on normalized position.

    Args:
        image_data: Full slide image bytes (PNG)
        position: Normalized position (0-1 coordinates)

    Returns:
        Cropped image bytes, or None if cropping fails
    """
    try:
        from PIL import Image

        img = Image.open(BytesIO(image_data))
        width, height = img.size

        # Convert normalized coords to pixels
        x1 = int(position.x * width)
        y1 = int(position.y * height)
        x2 = int((position.x + position.width) * width)
        y2 = int((position.y + position.height) * height)

        # Ensure valid crop bounds
        x1 = max(0, min(x1, width))
        x2 = max(0, min(x2, width))
        y1 = max(0, min(y1, height))
        y2 = max(0, min(y2, height))

        if x2 <= x1 or y2 <= y1:
            return None

        cropped = img.crop((x1, y1, x2, y2))

        buffer = BytesIO()
        cropped.save(buffer, format="PNG")
        return buffer.getvalue()

    except Exception as e:
        logger.debug(f"Failed to crop region: {e}")
        return None


def create_extract_images_node(
    config: HolisticConfig | None = None,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create an image extraction node for the holistic pipeline.

    This node extracts images from PDF slides, filtering out branding elements
    and small icons. The extracted images are then passed to the classification
    node for further processing.

    Args:
        config: Holistic processing configuration

    Returns:
        Node function for the LangGraph pipeline
    """
    resolved_config = config or HolisticConfig()

    def extract_images_node(state: dict[str, Any]) -> dict[str, Any]:
        """Extract and filter images from document slides.

        Args:
            state: Pipeline state with document and slides

        Returns:
            Updated state with extracted_images list
        """
        slides: list[Slide] = state.get("slides", [])
        document = state.get("document")
        pdf_data = document.pdf_data if document else state.get("pdf_data")

        if not slides:
            logger.warning("No slides available for image extraction")
            return {
                **state,
                "extracted_images": [],
                "current_step": "extract_images",
                "progress": 20,
            }

        if not resolved_config.extract_images:
            logger.info("Image extraction disabled, skipping")
            return {
                **state,
                "extracted_images": [],
                "current_step": "extract_images",
                "progress": 20,
            }

        extracted_images = _extract_images_from_slides(
            slides=slides,
            pdf_data=pdf_data,
            config=resolved_config,
        )

        return {
            **state,
            "extracted_images": extracted_images,
            "current_step": "extract_images",
            "progress": 20,
        }

    return extract_images_node
