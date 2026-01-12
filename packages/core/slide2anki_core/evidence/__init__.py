"""Evidence and image processing utilities."""

from slide2anki_core.evidence.bbox import denormalize_bbox, normalize_bbox
from slide2anki_core.evidence.crop import CropError, crop_evidence

__all__ = ["crop_evidence", "CropError", "normalize_bbox", "denormalize_bbox"]
