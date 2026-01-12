"""Evidence cropping utilities."""

from io import BytesIO

from slide2anki_core.evidence.bbox import denormalize_bbox
from slide2anki_core.schemas.claims import Evidence
from slide2anki_core.utils.logging import get_logger

logger = get_logger(__name__)


class CropError(Exception):
    """Error during image cropping."""

    pass


def crop_evidence(
    image_data: bytes,
    evidence: Evidence,
    padding: int = 10,
) -> bytes | None:
    """Crop evidence region from slide image.

    Args:
        image_data: Full slide image bytes
        evidence: Evidence with bounding box
        padding: Pixels to add around the crop

    Returns:
        Cropped image bytes, or None if no bbox

    Raises:
        CropError: If cropping fails due to invalid data
    """
    if not evidence.bbox:
        logger.debug("No bounding box in evidence, skipping crop")
        return None

    try:
        from PIL import Image

        # Load image
        image = Image.open(BytesIO(image_data))
        width, height = image.size
        logger.debug(f"Cropping from image {width}x{height}")

        # Get pixel coordinates
        x, y, w, h = denormalize_bbox(evidence.bbox, width, height)

        # Validate bbox dimensions
        if w <= 0 or h <= 0:
            logger.warning(f"Invalid bbox dimensions: w={w}, h={h}")
            return None

        # Add padding
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(width, x + w + padding)
        y2 = min(height, y + h + padding)

        # Validate crop region
        if x2 <= x1 or y2 <= y1:
            logger.warning(f"Invalid crop region: ({x1}, {y1}) to ({x2}, {y2})")
            return None

        logger.debug(f"Cropping region ({x1}, {y1}) to ({x2}, {y2})")

        # Crop
        cropped = image.crop((x1, y1, x2, y2))

        # Convert to bytes
        buffer = BytesIO()
        cropped.save(buffer, format="PNG")
        result = buffer.getvalue()
        logger.debug(f"Cropped image size: {len(result)} bytes")
        return result

    except FileNotFoundError as e:
        logger.error(f"Image file not found: {e}")
        raise CropError(f"Image file not found: {e}") from e
    except OSError as e:
        logger.error(f"Failed to open image: {e}")
        raise CropError(f"Failed to open image: {e}") from e
    except ValueError as e:
        logger.error(f"Invalid image data or bbox: {e}")
        raise CropError(f"Invalid image data or bbox: {e}") from e
    except Exception as e:
        # Log unexpected errors but still raise
        logger.exception(f"Unexpected error during crop: {e}")
        raise CropError(f"Unexpected error during crop: {e}") from e
