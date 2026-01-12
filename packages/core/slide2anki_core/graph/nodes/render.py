"""Render node: Convert PDF pages to images."""

from collections.abc import Callable
from io import BytesIO
from typing import Any

from slide2anki_core.schemas.document import Document, Slide


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

            # Convert PDF to images
            images = convert_from_bytes(
                document.pdf_data,
                dpi=dpi,
                fmt="PNG",
            )

            slides = []
            for i, image in enumerate(images):
                # Convert to bytes
                buffer = BytesIO()
                image.save(buffer, format="PNG")
                image_data = buffer.getvalue()

                slide = Slide(
                    page_index=i,
                    image_data=image_data,
                    width=image.width,
                    height=image.height,
                )
                slides.append(slide)

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
