"""Render node: Convert PDF pages to images."""

from collections.abc import Callable
from io import BytesIO
from typing import Any

from slide2anki_core.schemas.document import Document, Slide
from slide2anki_core.utils.logging import get_logger

logger = get_logger(__name__)

# Threshold for considering a page "text-only"
# If total image area is less than this fraction of page area, treat as text-only
IMAGE_AREA_THRESHOLD = 0.05  # 5% of page area

# Minimum image dimension to consider it meaningful (filters out tiny icons/bullets)
MIN_IMAGE_DIMENSION = 50  # pixels


def _analyze_page_content(
    pdf_data: bytes,
) -> list[tuple[bool, str | None]]:
    """Analyze PDF pages to detect text-only pages and extract text.

    Args:
        pdf_data: Raw PDF bytes

    Returns:
        List of (is_text_only, extracted_text) tuples for each page
    """
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not installed, skipping text-only detection")
        return []

    results: list[tuple[bool, str | None]] = []

    try:
        with pdfplumber.open(BytesIO(pdf_data)) as pdf:
            for page in pdf.pages:
                page_width = page.width
                page_height = page.height
                page_area = page_width * page_height

                # Get all images on the page
                images = page.images or []

                # Calculate total meaningful image area
                meaningful_image_area = 0.0
                for img in images:
                    img_width = abs(img.get("x1", 0) - img.get("x0", 0))
                    img_height = abs(img.get("top", 0) - img.get("bottom", 0))

                    # Skip tiny images (likely icons, bullets, logos)
                    if img_width < MIN_IMAGE_DIMENSION or img_height < MIN_IMAGE_DIMENSION:
                        continue

                    meaningful_image_area += img_width * img_height

                # Check if page is text-only
                image_ratio = meaningful_image_area / page_area if page_area > 0 else 0
                is_text_only = image_ratio < IMAGE_AREA_THRESHOLD

                # Extract text for text-only pages
                extracted_text = None
                if is_text_only:
                    try:
                        extracted_text = page.extract_text() or ""
                        # Clean up extracted text
                        extracted_text = extracted_text.strip()
                        if not extracted_text:
                            # No text extracted, might be a scanned page
                            is_text_only = False
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page: {e}")
                        is_text_only = False

                results.append((is_text_only, extracted_text))
                logger.debug(
                    f"Page analysis: is_text_only={is_text_only}, "
                    f"image_ratio={image_ratio:.2%}, "
                    f"text_len={len(extracted_text) if extracted_text else 0}"
                )

    except Exception as e:
        logger.warning(f"Failed to analyze PDF content: {e}")
        return []

    return results


def create_render_node(dpi: int = 200) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create a render node with specified DPI.

    Args:
        dpi: Resolution for rendering (default 200)

    Returns:
        Node function
    """

    def render_node(state: dict[str, Any]) -> dict[str, Any]:
        """Render PDF pages to images.

        Args:
            state: Pipeline state with document

        Returns:
            Updated state with slides
        """
        document: Document = state.get("document")
        if not document or not document.pdf_data:
            return {
                **state,
                "errors": state.get("errors", []) + ["No document to render"],
                "current_step": "render",
            }

        try:
            from pdf2image import convert_from_bytes

            # Analyze pages to detect text-only content
            page_analysis = _analyze_page_content(document.pdf_data)

            # Convert PDF to images
            images = convert_from_bytes(
                document.pdf_data,
                dpi=dpi,
                fmt="PNG",
            )

            slides = []
            text_only_count = 0
            for i, image in enumerate(images):
                # Convert to bytes
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                image_data = buffer.getvalue()

                # Get text-only analysis if available
                is_text_only = False
                extracted_text = None
                if i < len(page_analysis):
                    is_text_only, extracted_text = page_analysis[i]
                    if is_text_only:
                        text_only_count += 1

                slide = Slide(
                    page_index=i,
                    image_data=image_data,
                    width=image.width,
                    height=image.height,
                    is_text_only=is_text_only,
                    extracted_text=extracted_text,
                )
                slides.append(slide)

            logger.info(
                f"Rendered {len(slides)} pages, {text_only_count} text-only "
                f"({text_only_count / len(slides) * 100:.0f}% token savings potential)"
            )

            # Update document
            document.page_count = len(slides)
            document.slides = slides

            return {
                **state,
                "document": document,
                "slides": slides,
                "current_step": "render",
                "progress": 15,
            }

        except Exception as e:
            return {
                **state,
                "errors": state.get("errors", []) + [f"Render error: {str(e)}"],
                "current_step": "render",
            }

    return render_node
