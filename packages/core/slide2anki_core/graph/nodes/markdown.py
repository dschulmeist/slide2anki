"""Markdown node: Build structured markdown blocks from claims."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from slide2anki_core.schemas.claims import Claim, ClaimKind
from slide2anki_core.schemas.document import Document
from slide2anki_core.schemas.markdown import MarkdownBlock
from slide2anki_core.utils.hashing import content_hash


def _render_markdown(chapter_title: str, blocks: list[MarkdownBlock]) -> str:
    """Render markdown content for a chapter.

    Args:
        chapter_title: Title used for the chapter heading
        blocks: Ordered markdown blocks

    Returns:
        Markdown content for the chapter
    """
    lines = [f"## {chapter_title}", ""]
    for block in blocks:
        lines.append(f"<!-- block:{block.anchor_id} -->")
        lines.append(block.content)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def create_markdown_node() -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Create a markdown node for building blocks from claims.

    Returns:
        Node function
    """

    def markdown_node(state: dict[str, Any]) -> dict[str, Any]:
        """Build markdown blocks for a document.

        Args:
            state: Pipeline state with document and claims

        Returns:
            Updated state with markdown blocks and content
        """
        document: Document | None = state.get("document")
        claims: list[Claim] = state.get("claims", [])

        if not document:
            return {
                **state,
                "errors": state.get("errors", []) + ["No document for markdown"],
                "current_step": "markdown",
            }

        chapter_title = document.name
        blocks: list[MarkdownBlock] = []
        dedupe_map: dict[str, MarkdownBlock] = {}

        for claim in claims:
            content = claim.statement.strip()
            if claim.kind == ClaimKind.FORMULA:
                content = f"$$\n{content}\n$$"

            normalized = content.lower()
            existing = dedupe_map.get(normalized)
            if existing:
                existing.evidence.append(claim.evidence)
                continue

            anchor_source = f"{claim.kind.value}:{content}"
            anchor_id = content_hash(anchor_source)[:12]

            block = MarkdownBlock(
                anchor_id=anchor_id,
                kind=claim.kind.value,
                content=content,
                evidence=[claim.evidence],
                position_index=len(blocks),
                chapter_title=chapter_title,
            )
            blocks.append(block)
            dedupe_map[normalized] = block

        markdown_content = _render_markdown(chapter_title, blocks)

        return {
            **state,
            "markdown_blocks": blocks,
            "markdown_content": markdown_content,
            "current_step": "markdown",
            "progress": 65,
        }

    return markdown_node
