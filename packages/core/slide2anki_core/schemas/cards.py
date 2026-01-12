"""Flashcard schemas."""

from enum import Enum

from pydantic import BaseModel, Field

from slide2anki_core.schemas.claims import Evidence


class CardFlag(str, Enum):
    """Flags that can be applied to card drafts."""

    AMBIGUOUS = "ambiguous"
    TOO_LONG = "too_long"
    MISSING_CONTEXT = "missing_context"
    DUPLICATE = "duplicate"
    LOW_CONFIDENCE = "low_confidence"
    NEEDS_REVIEW = "needs_review"


class CardStatus(str, Enum):
    """Status of a card draft."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CardDraft(BaseModel):
    """A generated flashcard draft."""

    front: str = Field(..., description="Question/prompt side")
    back: str = Field(..., description="Answer side")
    tags: list[str] = Field(default_factory=list, description="Card tags")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Generation confidence")
    flags: list[CardFlag] = Field(default_factory=list, description="Quality flags")
    evidence: list[Evidence] = Field(
        default_factory=list, description="Source evidence"
    )
    status: CardStatus = Field(CardStatus.PENDING, description="Review status")
    critique: str | None = Field(None, description="Critique feedback")

    def __hash__(self) -> int:
        return hash((self.front, self.back))
