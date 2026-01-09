"""Document and slide schemas."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class Slide(BaseModel):
    """A single slide from a PDF."""

    page_index: int = Field(..., description="0-based page index")
    image_path: Optional[Path] = Field(None, description="Path to rendered image")
    image_data: Optional[bytes] = Field(None, description="Raw image bytes")
    width: int = Field(0, description="Image width in pixels")
    height: int = Field(0, description="Image height in pixels")

    class Config:
        arbitrary_types_allowed = True


class Document(BaseModel):
    """A PDF document being processed."""

    name: str = Field(..., description="Document/deck name")
    pdf_path: Optional[Path] = Field(None, description="Path to source PDF")
    pdf_data: Optional[bytes] = Field(None, description="Raw PDF bytes")
    page_count: int = Field(0, description="Number of pages")
    slides: list[Slide] = Field(default_factory=list, description="Rendered slides")

    class Config:
        arbitrary_types_allowed = True
