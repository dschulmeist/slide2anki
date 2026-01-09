"""Bounding box utilities."""

from typing import Tuple

from slide2anki_core.schemas.claims import BoundingBox


def normalize_bbox(
    x: int, y: int, width: int, height: int, image_width: int, image_height: int
) -> BoundingBox:
    """Convert pixel coordinates to normalized (0-1) coordinates.

    Args:
        x: X pixel coordinate
        y: Y pixel coordinate
        width: Width in pixels
        height: Height in pixels
        image_width: Total image width
        image_height: Total image height

    Returns:
        Normalized BoundingBox
    """
    return BoundingBox(
        x=x / image_width,
        y=y / image_height,
        width=width / image_width,
        height=height / image_height,
    )


def denormalize_bbox(
    bbox: BoundingBox, image_width: int, image_height: int
) -> Tuple[int, int, int, int]:
    """Convert normalized coordinates to pixel coordinates.

    Args:
        bbox: Normalized bounding box
        image_width: Total image width
        image_height: Total image height

    Returns:
        Tuple of (x, y, width, height) in pixels
    """
    return (
        int(bbox.x * image_width),
        int(bbox.y * image_height),
        int(bbox.width * image_width),
        int(bbox.height * image_height),
    )
