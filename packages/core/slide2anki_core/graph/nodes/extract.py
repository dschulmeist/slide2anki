"""Extract node: Identify claims from slides using vision model."""

from typing import Any, Callable

from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.claims import BoundingBox, Claim, ClaimKind, Evidence
from slide2anki_core.schemas.document import Slide

EXTRACT_PROMPT = """Analyze this lecture slide and extract atomic claims.

For each claim, identify:
1. Type: definition, fact, process, relationship, example, formula, or other
2. Statement: A clear, self-contained statement of the claim
3. Confidence: How confident you are (0.0-1.0)
4. Evidence: The slide region where the claim appears

Focus on:
- Definitions of key terms
- Important facts and data points
- Processes and sequences
- Relationships between concepts
- Formulas and equations

Output format (JSON object with a "claims" array):
{
  "claims": [
    {
      "kind": "definition",
      "statement": "Mitochondria are organelles that produce ATP through cellular respiration.",
      "confidence": 0.95,
      "evidence": {
        "bbox": {"x": 0.12, "y": 0.34, "width": 0.52, "height": 0.18},
        "text_snippet": "Mitochondria produce ATP through cellular respiration"
      }
    }
  ]
}

Evidence rules:
- bbox coordinates are normalized 0-1 relative to the slide image
- include only evidence that is explicitly visible on the slide
- if unsure about bbox, omit the evidence field entirely

Only include claims that are explicitly visible on the slide.
Do not infer or add information not shown.
"""


def create_extract_node(
    adapter: BaseModelAdapter,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create an extract node with the given model adapter.

    Args:
        adapter: Model adapter for vision calls

    Returns:
        Node function
    """

    async def extract_node(state: dict[str, Any]) -> dict[str, Any]:
        """Extract claims from each slide.

        Args:
            state: Pipeline state with slides

        Returns:
            Updated state with claims
        """
        slides: list[Slide] = state.get("slides", [])
        if not slides:
            return {
                **state,
                "errors": state.get("errors", []) + ["No slides to extract from"],
                "current_step": "extract",
            }

        all_claims: list[Claim] = []
        total_slides = len(slides)

        for i, slide in enumerate(slides):
            if not slide.image_data:
                continue

            try:
                # Call vision model
                response = await adapter.extract_claims(
                    image_data=slide.image_data,
                    prompt=EXTRACT_PROMPT,
                )

                # Parse claims from response
                for claim_data in response:
                    evidence_data = claim_data.get("evidence") or {}
                    bbox_data = evidence_data.get("bbox")
                    # Keep extraction resilient to malformed evidence payloads.
                    bbox = None
                    if isinstance(bbox_data, dict):
                        try:
                            bbox = BoundingBox(**bbox_data)
                        except Exception:
                            bbox = None
                    claim = Claim(
                        kind=ClaimKind(claim_data.get("kind", "other")),
                        statement=claim_data["statement"],
                        confidence=claim_data.get("confidence", 1.0),
                        evidence=Evidence(
                            slide_index=slide.page_index,
                            bbox=bbox,
                            text_snippet=evidence_data.get("text_snippet"),
                        ),
                    )
                    all_claims.append(claim)

            except Exception as e:
                # Log error but continue with other slides
                state.setdefault("errors", []).append(
                    f"Extract error on slide {i}: {str(e)}"
                )

            # Update progress (15-50% of total)
            progress = 15 + int(35 * (i + 1) / total_slides)
            state["progress"] = progress

        return {
            **state,
            "claims": all_claims,
            "current_step": "extract",
            "progress": 50,
        }

    return extract_node
