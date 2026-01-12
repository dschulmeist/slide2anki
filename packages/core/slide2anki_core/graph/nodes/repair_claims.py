"""Repair node: Fix unsupported claims within region evidence."""

from collections.abc import Callable
from typing import Any

from slide2anki_core.evidence.crop import crop_evidence
from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.claims import Claim, Evidence
from slide2anki_core.schemas.document import Slide
from slide2anki_core.schemas.regions import SlideRegion

REPAIR_PROMPT = """Rewrite the following claims so they are strictly supported by the slide region.

Rules:
- Stay within the evidence shown in the region.
- Keep the claim atomic and concise.
- If a claim cannot be supported, return an empty string.

Claims:
{claims}

Output format:
{{
  "repairs": [
    {{"index": 0, "statement": "Corrected statement"}}
  ]
}}
"""


def _format_claims(claims: list[Claim], indices: list[int]) -> str:
    """Format selected claims for the repair prompt."""
    lines: list[str] = []
    for index in indices:
        claim = claims[index]
        lines.append(f"{index}. [{claim.kind.value}] {claim.statement}")
    return "\n".join(lines)


def create_repair_claims_node(
    adapter: BaseModelAdapter,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create a repair node that rewrites unsupported claims.

    Args:
        adapter: Model adapter for vision calls

    Returns:
        Node function
    """

    async def repair_claims_node(state: dict[str, Any]) -> dict[str, Any]:
        """Repair claims that failed verification.

        Args:
            state: Pipeline state with failed claim indexes

        Returns:
            Updated state with repaired claims
        """
        claims: list[Claim] = state.get("claims", [])
        failed_claims: list[int] = state.get("failed_claims", [])
        suggestions: dict[int, str] = state.get("repair_suggestions", {})
        slide: Slide | None = state.get("slide")
        region: SlideRegion | None = state.get("region")

        if not claims or not failed_claims:
            return {
                **state,
                "current_step": "repair_claims",
                "attempt": state.get("attempt", 0),
            }

        image_data = slide.image_data if slide else None
        if slide and region:
            evidence = Evidence(slide_index=slide.page_index, bbox=region.bbox)
            region_image = crop_evidence(slide.image_data, evidence, padding=0)
            if region_image:
                image_data = region_image

        prompt = REPAIR_PROMPT.format(claims=_format_claims(claims, failed_claims))
        data = await adapter.generate_structured(prompt=prompt, image_data=image_data)
        repairs = []
        if isinstance(data, dict):
            repairs = data.get("repairs", [])
        elif isinstance(data, list):
            repairs = data

        repair_map: dict[int, str] = {
            index: suggestion for index, suggestion in suggestions.items()
        }
        for item in repairs:
            index = item.get("index")
            statement = item.get("statement")
            if isinstance(index, int) and isinstance(statement, str):
                repaired = statement.strip()
                repair_map[index] = repaired

        for index in failed_claims:
            new_statement = repair_map.get(index, "").strip()
            if new_statement:
                claims[index].statement = new_statement
                claims[index].confidence = min(max(claims[index].confidence, 0.5), 0.7)

        attempt = state.get("attempt", 0) + 1

        return {
            **state,
            "claims": claims,
            "attempt": attempt,
            "current_step": "repair_claims",
        }

    return repair_claims_node
