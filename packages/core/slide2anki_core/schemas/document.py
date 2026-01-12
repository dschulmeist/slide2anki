"""Document and slide schemas."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Slide(BaseModel):
    """A single slide from a PDF."""

    page_index: int = Field(..., description="0-based page index")
    image_path: Path | None = Field(None, description="Path to rendered image")
    image_data: bytes | None = Field(None, description="Raw image bytes")
    width: int = Field(0, description="Image width in pixels")
    height: int = Field(0, description="Image height in pixels")
    is_text_only: bool = Field(
        False, description="True if page has no meaningful images/diagrams"
    )
    extracted_text: str | None = Field(
        None, description="Text extracted directly from PDF for text-only pages"
    )
    model_config = ConfigDict(arbitrary_types_allowed=True)


class Document(BaseModel):
    """A PDF document being processed."""

    name: str = Field(..., description="Document/deck name")
    pdf_path: Path | None = Field(None, description="Path to source PDF")
    pdf_data: bytes | None = Field(None, description="Raw PDF bytes")
    page_count: int = Field(0, description="Number of pages")
    slides: list[Slide] = Field(default_factory=list, description="Rendered slides")
    model_config = ConfigDict(arbitrary_types_allowed=True)
