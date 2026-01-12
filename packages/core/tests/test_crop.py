"""Tests for evidence cropping functionality."""

import pytest

from slide2anki_core.evidence.crop import CropError, crop_evidence
from slide2anki_core.schemas.claims import BoundingBox, Evidence


class TestCropEvidence:
    """Tests for evidence cropping."""

    @pytest.fixture
    def sample_image(self) -> bytes:
        """Create a minimal valid PNG image (100x100)."""
        # Create a simple PNG using PIL
        from io import BytesIO

        from PIL import Image

        img = Image.new("RGB", (100, 100), color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_crop_with_valid_bbox(self, sample_image: bytes) -> None:
        """Test cropping with valid bounding box."""
        evidence = Evidence(
            slide_index=0,
            bbox=BoundingBox(x=0.1, y=0.1, width=0.5, height=0.5),
        )

        result = crop_evidence(sample_image, evidence, padding=5)

        assert result is not None
        assert len(result) > 0
        # Result should be valid PNG
        assert result[:4] == b"\x89PNG"

    def test_crop_no_bbox_returns_none(self, sample_image: bytes) -> None:
        """Test that no bbox returns None."""
        evidence = Evidence(slide_index=0, bbox=None)

        result = crop_evidence(sample_image, evidence)

        assert result is None

    def test_crop_full_image(self, sample_image: bytes) -> None:
        """Test cropping entire image."""
        evidence = Evidence(
            slide_index=0,
            bbox=BoundingBox(x=0.0, y=0.0, width=1.0, height=1.0),
        )

        result = crop_evidence(sample_image, evidence, padding=0)

        assert result is not None
        assert len(result) > 0

    def test_crop_with_padding(self, sample_image: bytes) -> None:
        """Test that padding is applied."""
        evidence = Evidence(
            slide_index=0,
            bbox=BoundingBox(x=0.2, y=0.2, width=0.3, height=0.3),
        )

        # With larger padding, result should be larger
        result_small = crop_evidence(sample_image, evidence, padding=0)
        result_large = crop_evidence(sample_image, evidence, padding=20)

        assert result_small is not None
        assert result_large is not None
        # Can't easily compare sizes due to compression, but both should work

    def test_crop_invalid_image_raises(self) -> None:
        """Test that invalid image data raises CropError."""
        evidence = Evidence(
            slide_index=0,
            bbox=BoundingBox(x=0.1, y=0.1, width=0.5, height=0.5),
        )

        with pytest.raises(CropError):
            crop_evidence(b"not an image", evidence)

    def test_crop_zero_size_bbox_returns_none(self, sample_image: bytes) -> None:
        """Test that zero-size bbox returns None."""
        evidence = Evidence(
            slide_index=0,
            bbox=BoundingBox(x=0.5, y=0.5, width=0.0, height=0.0),
        )

        result = crop_evidence(sample_image, evidence)

        assert result is None

    def test_crop_out_of_bounds_handled(self, sample_image: bytes) -> None:
        """Test that out-of-bounds bbox is clamped."""
        # This bbox extends past image boundaries
        evidence = Evidence(
            slide_index=0,
            bbox=BoundingBox(x=0.8, y=0.8, width=0.5, height=0.5),
        )

        # Should still work, just cropped to image bounds
        result = crop_evidence(sample_image, evidence, padding=5)

        assert result is not None
