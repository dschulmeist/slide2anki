"""Evidence cropping utilities."""

from io import BytesIO
from typing import Optional

from slide2anki_core.schemas.claims import BoundingBox, Evidence
from slide2anki_core.evidence.bbox import denormalize_bbox


def crop_evidence(
    image_data: bytes,
    evidence: Evidence,
    padding: int = 10,
) -> Optional[bytes]:
    """Crop evidence region from slide image.

    Args:
        image_data: Full slide image bytes
        evidence: Evidence with bounding box
        padding: Pixels to add around the crop

    Returns:
        Cropped image bytes, or None if no bbox
    """
    if not evidence.bbox:
        return None

    try:
        from PIL import Image

        # Load image
        image = Image.open(BytesIO(image_data))
        width, height = image.size

        # Get pixel coordinates
        x, y, w, h = denormalize_bbox(evidence.bbox, width, height)

        # Add padding
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(width, x + w + padding)
        y2 = min(height, y + h + padding)

        # Crop
        cropped = image.crop((x1, y1, x2, y2))

        # Convert to bytes
        buffer = BytesIO()
        cropped.save(buffer, format="PNG")
        return buffer.getvalue()

    except Exception:
        return None
