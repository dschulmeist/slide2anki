"""Tests for image processing schemas.

This module tests the image-related schemas used in the holistic pipeline
for image extraction, classification, and processing.
"""

from slide2anki_core.schemas.images import (
    ExtractedImage,
    ImagePosition,
    ImageType,
    ProcessedImage,
)


class TestImagePosition:
    """Tests for the ImagePosition schema."""

    def test_area_calculation(self):
        """Test that area is calculated correctly."""
        pos = ImagePosition(x=0.0, y=0.0, width=0.5, height=0.4)
        assert pos.area == 0.2  # 0.5 * 0.4

    def test_center_y_calculation(self):
        """Test that center_y is calculated correctly."""
        pos = ImagePosition(x=0.0, y=0.2, width=0.5, height=0.4)
        assert pos.center_y == 0.4  # 0.2 + 0.4/2

    def test_is_in_header(self):
        """Test header detection."""
        # Image in top 10% of slide
        header_pos = ImagePosition(x=0.0, y=0.0, width=0.5, height=0.1)
        assert header_pos.is_in_header(threshold=0.15) is True

        # Image in middle of slide
        middle_pos = ImagePosition(x=0.0, y=0.4, width=0.5, height=0.2)
        assert middle_pos.is_in_header(threshold=0.15) is False

    def test_is_in_footer(self):
        """Test footer detection."""
        # Image in bottom 10% of slide
        footer_pos = ImagePosition(x=0.0, y=0.9, width=0.5, height=0.1)
        assert footer_pos.is_in_footer(threshold=0.15) is True

        # Image in middle of slide
        middle_pos = ImagePosition(x=0.0, y=0.4, width=0.5, height=0.2)
        assert middle_pos.is_in_footer(threshold=0.15) is False


class TestImageType:
    """Tests for the ImageType enum."""

    def test_all_types_defined(self):
        """Test that all expected image types are defined."""
        expected_types = [
            "formula",
            "diagram",
            "chart",
            "code",
            "table",
            "photo",
            "logo",
            "decorative",
            "unknown",
        ]
        actual_types = [t.value for t in ImageType]
        assert sorted(actual_types) == sorted(expected_types)


class TestExtractedImage:
    """Tests for the ExtractedImage schema."""

    def test_create_extracted_image(self):
        """Test creating an ExtractedImage."""
        pos = ImagePosition(x=0.1, y=0.2, width=0.3, height=0.4)
        img = ExtractedImage(
            image_id="img_0001",
            slide_index=5,
            position=pos,
            image_data=b"fake_image_data",
            occurrence_count=2,
        )

        assert img.image_id == "img_0001"
        assert img.slide_index == 5
        assert img.position.x == 0.1
        assert img.occurrence_count == 2


class TestProcessedImage:
    """Tests for the ProcessedImage schema."""

    def test_to_markdown_formula(self):
        """Test markdown generation for formulas."""
        pos = ImagePosition(x=0.1, y=0.2, width=0.3, height=0.4)
        img = ProcessedImage(
            image_id="img_0001",
            slide_index=0,
            image_type=ImageType.FORMULA,
            position=pos,
            transcription="E = mc^2",
            should_embed=False,
        )

        md = img.to_markdown()
        assert "$$" in md
        assert "E = mc^2" in md

    def test_to_markdown_code(self):
        """Test markdown generation for code."""
        pos = ImagePosition(x=0.1, y=0.2, width=0.3, height=0.4)
        img = ProcessedImage(
            image_id="img_0001",
            slide_index=0,
            image_type=ImageType.CODE,
            position=pos,
            transcription="```python\nprint('hello')\n```",
            should_embed=False,
        )

        md = img.to_markdown()
        assert "```" in md
        assert "print('hello')" in md

    def test_to_markdown_description(self):
        """Test markdown generation for diagrams with description."""
        pos = ImagePosition(x=0.1, y=0.2, width=0.3, height=0.4)
        img = ProcessedImage(
            image_id="img_0001",
            slide_index=0,
            image_type=ImageType.DIAGRAM,
            position=pos,
            description="A flowchart showing the process",
            should_embed=False,
        )

        md = img.to_markdown()
        assert "flowchart" in md

    def test_to_markdown_empty(self):
        """Test markdown generation with no content."""
        pos = ImagePosition(x=0.1, y=0.2, width=0.3, height=0.4)
        img = ProcessedImage(
            image_id="img_0001",
            slide_index=0,
            image_type=ImageType.UNKNOWN,
            position=pos,
            should_embed=False,
        )

        md = img.to_markdown()
        assert md == ""
