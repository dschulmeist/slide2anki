"""Markdown block schemas for the canonical knowledge base."""

from pydantic import BaseModel, Field

from slide2anki_core.schemas.claims import Evidence


class MarkdownBlock(BaseModel):
    """A structured markdown block with evidence and ordering."""

    anchor_id: str = Field(..., description="Stable anchor ID for the block")
    kind: str = Field(..., description="Block type (definition, fact, formula, etc.)")
    content: str = Field(..., description="Markdown content for the block")
    evidence: list[Evidence] = Field(
        default_factory=list, description="Evidence references for the block"
    )
    position_index: int = Field(0, description="Ordering index within the chapter")
    chapter_title: str = Field(..., description="Chapter title for the block")
