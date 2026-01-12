"""Extract node: Identify claims from a slide region."""

from collections.abc import Callable
from typing import Any

from slide2anki_core.evidence.crop import CropError, crop_evidence
from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.claims import BoundingBox, Claim, ClaimKind, Evidence
from slide2anki_core.schemas.document import Slide
from slide2anki_core.schemas.regions import SlideRegion
from slide2anki_core.utils.logging import get_logger

logger = get_logger(__name__)

EXTRACT_REGION_PROMPT = """Analyze this slide region and extract atomic claims.

For each claim, identify:
1. Type: definition, fact, process, relationship, example, formula, or other
2. Statement: A clear, self-contained statement of the claim
3. Confidence: How confident you are (0.0-1.0)
4. Evidence: The region bounding box where the claim appears

Output format (JSON object with a "claims" array):
{
  "claims": [
    {
      "kind": "definition",
      "statement": "Mitochondria produce ATP through cellular respiration.",
      "confidence": 0.95,
      "evidence": {
        "bbox": {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.2},
        "text_snippet": "Mitochondria produce ATP"
      }
    }
  ]
}

Evidence rules:
- bbox coordinates are normalized 0-1 relative to the region image
- include only evidence that is explicitly visible
- if unsure about bbox, omit the evidence field entirely

Formula rules:
- if kind is "formula", the statement should be LaTeX only (no surrounding $)
"""

EXTRACT_TEXT_PROMPT = """Analyze this slide text and extract atomic claims.

The slide text is:
---
{text}
---

For each claim, identify:
1. Type: definition, fact, process, relationship, example, formula, or other
2. Statement: A clear, self-contained statement of the claim
3. Confidence: How confident you are (0.0-1.0)

Output format (JSON object with a "claims" array):
{{
  "claims": [
    {{
      "kind": "definition",
      "statement": "Mitochondria produce ATP through cellular respiration.",
      "confidence": 0.95,
      "evidence": {{
        "text_snippet": "Mitochondria produce ATP"
      }}
    }}
  ]
}}

Formula rules:
- if kind is "formula", the statement should be LaTeX only (no surrounding $)
"""


def _convert_bbox_to_slide(
    region_bbox: BoundingBox,
    local_bbox: BoundingBox,
) -> BoundingBox:
    """Convert a region-local bbox into slide-normalized coordinates."""
    return BoundingBox(
        x=region_bbox.x + local_bbox.x * region_bbox.width,
        y=region_bbox.y + local_bbox.y * region_bbox.height,
        width=local_bbox.width * region_bbox.width,
        height=local_bbox.height * region_bbox.height,
    )


def create_extract_region_node(
    adapter: BaseModelAdapter,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create an extraction node for slide regions.

    Args:
        adapter: Model adapter for vision calls

    Returns:
        Node function
    """

    async def extract_region_node(state: dict[str, Any]) -> dict[str, Any]:
        """Extract claims from a slide region.

        Args:
            state: Pipeline state with slide and region

        Returns:
            Updated state with claims
        """
        slide: Slide | None = state.get("slide")
        region: SlideRegion | None = state.get("region")
        if not slide or not region:
            return {
                **state,
                "claims": [],
                "current_step": "extract_region",
            }

        # For text-only slides, use text model instead of vision
        if slide.is_text_only and slide.extracted_text:
            logger.info(
                f"Extracting claims from text-only slide {slide.page_index} "
                f"({len(slide.extracted_text)} chars)"
            )
            prompt = EXTRACT_TEXT_PROMPT.format(text=slide.extracted_text)
            response = await adapter.generate_structured(prompt=prompt)
            if isinstance(response, dict):
                response = response.get("claims", [])
        else:
            if not slide.image_data:
                return {
                    **state,
                    "claims": [],
                    "current_step": "extract_region",
                }

            # Try to crop the region, fall back to full slide if cropping fails
            image_data = slide.image_data
            evidence = Evidence(slide_index=slide.page_index, bbox=region.bbox)
            try:
                region_image = crop_evidence(slide.image_data, evidence, padding=0)
                if region_image:
                    image_data = region_image
            except CropError as e:
                logger.warning(f"Failed to crop region, using full slide: {e}")

            logger.info(f"Extracting claims from region ({region.kind.value})")

            response = await adapter.extract_claims(
                image_data=image_data,
                prompt=EXTRACT_REGION_PROMPT,
            )

        claims: list[Claim] = []
        for claim_data in response:
            evidence_data = claim_data.get("evidence") or {}
            bbox_data = evidence_data.get("bbox")
            bbox = None
            if isinstance(bbox_data, dict):
                try:
                    local_bbox = BoundingBox(**bbox_data)
                    bbox = _convert_bbox_to_slide(region.bbox, local_bbox)
                except Exception:
                    bbox = None
            kind_value = claim_data.get("kind", "other")
            try:
                claim_kind = ClaimKind(kind_value)
            except ValueError:
                claim_kind = ClaimKind.OTHER
            claim = Claim(
                kind=claim_kind,
                statement=claim_data.get("statement", "").strip(),
                confidence=claim_data.get("confidence", 1.0),
                evidence=Evidence(
                    slide_index=slide.page_index,
                    bbox=bbox,
                    text_snippet=evidence_data.get("text_snippet"),
                ),
            )
            if claim.statement:
                claims.append(claim)

        logger.info(f"Extracted {len(claims)} claims from region")

        return {
            **state,
            "claims": claims,
            "current_step": "extract_region",
        }

    return extract_region_node
