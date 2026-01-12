"""Tests for LangGraph pipeline behavior."""

from typing import Any

import pytest

from slide2anki_core.graph import GraphConfig, build_card_graph, build_slide_graph
from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim, Evidence
from slide2anki_core.schemas.document import Slide


class FakeAdapter(BaseModelAdapter):
    """Deterministic adapter for graph tests."""

    async def extract_claims(
        self,
        image_data: bytes,
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Return a single claim that requires repair."""
        return [
            {
                "kind": "fact",
                "statement": "Wrong",
                "confidence": 0.6,
                "evidence": {"bbox": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}},
            }
        ]

    async def generate_structured(
        self,
        prompt: str,
        image_data: bytes | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Return structured JSON based on the prompt content."""
        if "Segment this slide" in prompt:
            return {
                "regions": [
                    {
                        "kind": "bullets",
                        "bbox": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
                        "confidence": 1.0,
                    }
                ]
            }
        if "Verify each claim" in prompt:
            verdict = "supported" if "Correct" in prompt else "unsupported"
            payload = {"index": 0, "verdict": verdict, "reason": "test"}
            if verdict == "unsupported":
                payload["suggested_statement"] = "Correct"
            return {"verifications": [payload]}
        if "Rewrite the following claims" in prompt:
            return {"repairs": [{"index": 0, "statement": "Correct"}]}
        if "Rewrite the following flashcards" in prompt:
            return {
                "repairs": [
                    {"index": 0, "front": "Good question", "back": "Good answer"}
                ]
            }
        return {}

    async def generate_cards(
        self,
        claims: list[Claim],
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Return a single card that needs repair."""
        return [
            {
                "front": "Bad question",
                "back": "Bad answer",
                "tags": [],
                "confidence": 0.6,
            }
        ]

    async def critique_cards(
        self,
        cards: list[CardDraft],
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Flag cards that still include the word 'Bad'."""
        if "Bad question" in prompt:
            return [
                {
                    "index": 0,
                    "flags": ["ambiguous"],
                    "critique": "Too vague.",
                }
            ]
        return []


@pytest.mark.asyncio
async def test_slide_graph_repairs_claims() -> None:
    """Ensure slide graph repairs unsupported claims."""
    graph = build_slide_graph(FakeAdapter(), GraphConfig(max_claim_repairs=1))
    slide = Slide(page_index=0, image_data=b"fake", width=100, height=100)
    result = await graph.ainvoke({"slide": slide})

    claims = result.get("claims", [])
    assert claims
    assert claims[0].statement == "Correct"


@pytest.mark.asyncio
async def test_card_graph_repairs_cards() -> None:
    """Ensure card graph repairs critiqued cards."""
    graph = build_card_graph(FakeAdapter(), GraphConfig(max_card_repairs=1))
    claims = [
        Claim(
            kind="fact",
            statement="Seed claim",
            confidence=0.9,
            evidence=Evidence(slide_index=0),
        )
    ]
    result = await graph.ainvoke({"claims": claims})

    cards = result.get("cards", [])
    assert cards
    assert cards[0].front == "Good question"
    assert cards[0].back == "Good answer"
