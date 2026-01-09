"""Evidence and image processing utilities."""

from slide2anki_core.evidence.crop import crop_evidence
from slide2anki_core.evidence.bbox import normalize_bbox, denormalize_bbox

__all__ = ["crop_evidence", "normalize_bbox", "denormalize_bbox"]
