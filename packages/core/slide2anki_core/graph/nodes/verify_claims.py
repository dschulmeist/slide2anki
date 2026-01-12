"""Verify node: Validate claims against region evidence."""

from collections.abc import Callable
from typing import Any

from slide2anki_core.evidence.crop import CropError, crop_evidence
from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.claims import Claim, Evidence
from slide2anki_core.schemas.document import Slide
from slide2anki_core.schemas.regions import SlideRegion
from slide2anki_core.utils.logging import get_logger

logger = get_logger(__name__)

VERIFY_PROMPT = """Verify each claim against the provided slide region.

Return a JSON object with a "verifications" array. Each item must include:
- index: index of the claim
- verdict: supported, unsupported, or unclear
- reason: short explanation
- suggested_statement: optional rewrite that stays within the evidence

Claims:
{claims}

Output format:
{{
  "verifications": [
    {{
      "index": 0,
      "verdict": "supported",
      "reason": "Exact wording appears in the region."
    }}
  ]
}}
"""


def _format_claims(claims: list[Claim]) -> str:
    """Format claims for verification prompt."""
    return "\n".join(
        f"{index}. [{claim.kind.value}] {claim.statement}"
        for index, claim in enumerate(claims)
    )


def create_verify_claims_node(
    adapter: BaseModelAdapter,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create a verification node that checks claim evidence.

    Args:
        adapter: Model adapter for vision calls

    Returns:
        Node function
    """

    async def verify_claims_node(state: dict[str, Any]) -> dict[str, Any]:
        """Verify extracted claims against slide evidence.

        Args:
            state: Pipeline state with claims, slide, and region

        Returns:
            Updated state with verification metadata
        """
        claims: list[Claim] = state.get("claims", [])
        slide: Slide | None = state.get("slide")
        region: SlideRegion | None = state.get("region")

        if not claims:
            return {
                **state,
                "needs_repair": False,
                "failed_claims": [],
                "repair_suggestions": {},
                "current_step": "verify_claims",
            }

        image_data = slide.image_data if slide else None
        if slide and region:
            evidence = Evidence(slide_index=slide.page_index, bbox=region.bbox)
            try:
                region_image = crop_evidence(slide.image_data, evidence, padding=0)
                if region_image:
                    image_data = region_image
            except CropError as e:
                # Fall back to full slide image if cropping fails
                logger.warning(f"Failed to crop region, using full slide: {e}")

        prompt = VERIFY_PROMPT.format(claims=_format_claims(claims))
        data = await adapter.generate_structured(prompt=prompt, image_data=image_data)
        verifications = []
        if isinstance(data, dict):
            verifications = data.get("verifications", [])
        elif isinstance(data, list):
            verifications = data

        failed_claims: list[int] = []
        repair_suggestions: dict[int, str] = {}

        # Create a copy of claims to avoid mutating state in place
        updated_claims = list(claims)

        for item in verifications:
            index = item.get("index")
            verdict = str(item.get("verdict", "")).lower()
            if not isinstance(index, int) or index < 0 or index >= len(updated_claims):
                continue
            if verdict in {"unsupported", "unclear"}:
                failed_claims.append(index)
                suggestion = item.get("suggested_statement")
                if isinstance(suggestion, str) and suggestion.strip():
                    repair_suggestions[index] = suggestion.strip()
                # Create new Claim with updated confidence (immutable update)
                old_claim = updated_claims[index]
                updated_claims[index] = old_claim.model_copy(
                    update={"confidence": min(old_claim.confidence, 0.4)}
                )
            elif verdict == "supported":
                # Create new Claim with updated confidence (immutable update)
                old_claim = updated_claims[index]
                updated_claims[index] = old_claim.model_copy(
                    update={"confidence": max(old_claim.confidence, 0.6)}
                )

        needs_repair = bool(failed_claims)
        claims = updated_claims
        logger.info(f"Verified {len(claims)} claims, {len(failed_claims)} need repair")

        return {
            **state,
            "claims": claims,
            "needs_repair": needs_repair,
            "failed_claims": failed_claims,
            "repair_suggestions": repair_suggestions,
            "current_step": "verify_claims",
        }

    return verify_claims_node
