"""Image extraction and processing schemas.

This module defines schemas for image extraction, classification, and processing
within the holistic document processing pipeline. Images are extracted from PDF
slides, classified by type (formula, diagram, chart, etc.), and then either
transcribed to text/LaTeX or described for embedding in the markdown document.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ImageType(str, Enum):
    """Classification of image content type.

    Used to route images to appropriate processing handlers:
    - FORMULA: Mathematical equations/formulas -> transcribe to LaTeX
    - DIAGRAM: Flowcharts, architectures, pipelines -> describe + embed
    - CHART: Data visualizations (graphs, plots) -> describe what they show
    - CODE: Screenshots of code -> transcribe to code block
    - TABLE: Data tables -> transcribe to markdown table
    - PHOTO: Real-world photographs -> describe + embed if relevant
    - LOGO: University, company, lab logos -> skip
    - DECORATIVE: Stock images, icons, generic illustrations -> skip
    - UNKNOWN: Could not classify -> manual review
    """

    FORMULA = "formula"
    DIAGRAM = "diagram"
    CHART = "chart"
    CODE = "code"
    TABLE = "table"
    PHOTO = "photo"
    LOGO = "logo"
    DECORATIVE = "decorative"
    UNKNOWN = "unknown"


class ImagePosition(BaseModel):
    """Position of an image on a slide.

    All coordinates are normalized to 0-1 range relative to slide dimensions.
    This allows position-based filtering (e.g., skip header/footer regions).
    """

    x: float = Field(..., ge=0.0, le=1.0, description="Left edge (0-1 normalized)")
    y: float = Field(..., ge=0.0, le=1.0, description="Top edge (0-1 normalized)")
    width: float = Field(..., ge=0.0, le=1.0, description="Width (0-1 normalized)")
    height: float = Field(..., ge=0.0, le=1.0, description="Height (0-1 normalized)")

    @property
    def area(self) -> float:
        """Calculate the area as a fraction of slide area (0-1)."""
        return self.width * self.height

    @property
    def center_y(self) -> float:
        """Calculate vertical center position (0-1)."""
        return self.y + self.height / 2

    def is_in_header(self, threshold: float = 0.15) -> bool:
        """Check if image is in the header region (top portion of slide).

        Args:
            threshold: Fraction of slide height considered header (default 15%)

        Returns:
            True if image center is in header region
        """
        return self.center_y < threshold

    def is_in_footer(self, threshold: float = 0.15) -> bool:
        """Check if image is in the footer region (bottom portion of slide).

        Args:
            threshold: Fraction of slide height considered footer (default 15%)

        Returns:
            True if image center is in footer region
        """
        return self.center_y > (1.0 - threshold)


class ExtractedImage(BaseModel):
    """An image extracted from a PDF slide before classification.

    Represents the raw extracted image with metadata about its source location.
    This is an intermediate representation before classification and processing.
    """

    image_id: str = Field(..., description="Unique identifier for this image")
    slide_index: int = Field(..., description="Source slide page index (0-based)")
    position: ImagePosition = Field(..., description="Position on the slide")
    image_data: bytes = Field(..., description="Raw PNG image bytes")
    occurrence_count: int = Field(
        1, description="Number of slides this image appears on"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ProcessedImage(BaseModel):
    """A fully processed image ready for markdown embedding.

    After classification and transcription/description, images become
    ProcessedImage instances that can be embedded in the final markdown.
    """

    image_id: str = Field(..., description="Unique identifier matching ExtractedImage")
    slide_index: int = Field(..., description="Source slide page index (0-based)")
    image_type: ImageType = Field(..., description="Classified image type")
    position: ImagePosition = Field(..., description="Position on the slide")

    # Processing results - one of these will be populated based on image_type
    transcription: str | None = Field(
        None,
        description="Transcribed content (LaTeX for formulas, code for code blocks, "
        "markdown for tables)",
    )
    description: str | None = Field(
        None,
        description="Natural language description for diagrams, charts, photos",
    )

    # Whether to embed the image itself in markdown (vs just transcription)
    should_embed: bool = Field(
        False,
        description="True if original image should be embedded in markdown",
    )
    image_data: bytes | None = Field(
        None,
        description="Original image bytes (only if should_embed=True)",
    )

    # Classification confidence
    confidence: float = Field(
        1.0, ge=0.0, le=1.0, description="Classification confidence"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_markdown(self) -> str:
        """Convert processed image to markdown representation.

        Returns:
            Markdown string for this image's content
        """
        if self.image_type == ImageType.FORMULA and self.transcription:
            # LaTeX formula - wrap in display math
            return f"$$\n{self.transcription}\n$$"

        if self.image_type == ImageType.CODE and self.transcription:
            # Code block - wrap in fenced code
            return f"```\n{self.transcription}\n```"

        if self.image_type == ImageType.TABLE and self.transcription:
            # Table - already in markdown format
            return self.transcription

        if self.description:
            # For diagrams, charts, photos - use description
            if self.should_embed:
                # Image will be embedded, add description as caption
                return f"*{self.description}*"
            # Just the description
            return self.description

        return ""
