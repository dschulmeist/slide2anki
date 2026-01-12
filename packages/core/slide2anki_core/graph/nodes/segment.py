"""Segment node: Identify layout regions on a slide."""

from collections.abc import Callable
from typing import Any

from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.claims import BoundingBox
from slide2anki_core.schemas.document import Slide
from slide2anki_core.schemas.regions import RegionKind, SlideRegion

SEGMENT_PROMPT = """Segment this slide into labeled regions.

Return a JSON object with a "regions" array. Each region must include:
- kind: title, bullets, table, equation, diagram, image, or other
- bbox: normalized coordinates in the slide (0-1)
- confidence: 0-1 confidence score
- text_snippet: short text description if visible (optional)

Output format:
{
  "regions": [
    {
      "kind": "title",
      "bbox": {"x": 0.05, "y": 0.04, "width": 0.9, "height": 0.12},
      "confidence": 0.9,
      "text_snippet": "Cellular respiration"
    }
  ]
}
"""


def _fallback_region() -> SlideRegion:
    """Return a default region covering the full slide."""
    return SlideRegion(
        kind=RegionKind.OTHER,
        bbox=BoundingBox(x=0.0, y=0.0, width=1.0, height=1.0),
        confidence=1.0,
    )


def create_segment_node(
    adapter: BaseModelAdapter,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create a segmentation node with the given model adapter.

    Args:
        adapter: Model adapter for vision calls

    Returns:
        Node function
    """

    async def segment_node(state: dict[str, Any]) -> dict[str, Any]:
        """Segment a slide into regions for extraction.

        Args:
            state: Pipeline state with a slide

        Returns:
            Updated state with regions
        """
        slide: Slide | None = state.get("slide")
        if not slide or not slide.image_data:
            return {
                **state,
                "regions": [_fallback_region()],
                "current_step": "segment",
            }

        data = await adapter.generate_structured(
            prompt=SEGMENT_PROMPT,
            image_data=slide.image_data,
        )
        regions_raw: list[dict[str, Any]] = []
        if isinstance(data, dict):
            regions_raw = data.get("regions", [])
        elif isinstance(data, list):
            regions_raw = data

        regions: list[SlideRegion] = []
        for raw in regions_raw:
            try:
                kind_value = raw.get("kind", RegionKind.OTHER)
                if not isinstance(kind_value, RegionKind):
                    try:
                        kind_value = RegionKind(str(kind_value))
                    except ValueError:
                        kind_value = RegionKind.OTHER
                region = SlideRegion(
                    kind=kind_value,
                    bbox=BoundingBox(**raw.get("bbox", {})),
                    confidence=raw.get("confidence", 1.0),
                    text_snippet=raw.get("text_snippet"),
                )
                regions.append(region)
            except Exception:
                continue

        if not regions:
            regions = [_fallback_region()]

        return {
            **state,
            "regions": regions,
            "current_step": "segment",
        }

    return segment_node
