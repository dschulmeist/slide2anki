"""Claim and evidence schemas for knowledge extraction.

This module defines schemas for extracted claims and their evidence linking
back to source slides. Claims are atomic pieces of knowledge (definitions,
facts, formulas, etc.) extracted from document content.

Note: The holistic pipeline produces markdown directly rather than claims,
but claims are still used for evidence traceability and card generation.
"""

from enum import Enum

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """A bounding box region on a slide."""

    x: float = Field(..., description="X coordinate (0-1 normalized)")
    y: float = Field(..., description="Y coordinate (0-1 normalized)")
    width: float = Field(..., description="Width (0-1 normalized)")
    height: float = Field(..., description="Height (0-1 normalized)")


class Evidence(BaseModel):
    """Evidence linking a claim to its source."""

    document_id: str | None = Field(
        None, description="Optional document identifier for multi-doc projects"
    )
    slide_index: int = Field(..., description="Which slide this evidence is from")
    bbox: BoundingBox | None = Field(None, description="Region on the slide")
    text_snippet: str | None = Field(None, description="Relevant text excerpt")


class ClaimKind(str, Enum):
    """Types of claims that can be extracted."""

    DEFINITION = "definition"
    FACT = "fact"
    PROCESS = "process"
    RELATIONSHIP = "relationship"
    EXAMPLE = "example"
    FORMULA = "formula"
    OTHER = "other"


class Claim(BaseModel):
    """An atomic piece of knowledge extracted from a slide."""

    kind: ClaimKind = Field(..., description="Type of claim")
    statement: str = Field(..., description="The claim statement")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Extraction confidence")
    evidence: Evidence = Field(..., description="Source evidence")

    def __hash__(self) -> int:
        """Provide a stable hash for claim deduplication."""
        return hash((self.kind, self.statement, self.evidence.slide_index))
