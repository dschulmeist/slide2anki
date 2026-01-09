"""OpenAI model adapter."""

import base64
import json
from typing import Any, Optional

from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim


class OpenAIAdapter(BaseModelAdapter):
    """Adapter for OpenAI models (GPT-4 Vision, GPT-4)."""

    def __init__(
        self,
        api_key: str,
        vision_model: str = "gpt-4o",
        text_model: str = "gpt-4o",
        base_url: Optional[str] = None,
    ):
        """Initialize the OpenAI adapter.

        Args:
            api_key: OpenAI API key
            vision_model: Model for vision tasks
            text_model: Model for text tasks
            base_url: Optional custom base URL
        """
        self.api_key = api_key
        self.vision_model = vision_model
        self.text_model = text_model
        self.base_url = base_url

        self._client: Any = None

    @property
    def client(self) -> Any:
        """Lazy-load the OpenAI client."""
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    async def extract_claims(
        self,
        image_data: bytes,
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Extract claims from a slide image using vision model."""
        # Encode image as base64
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        response = await self.client.chat.completions.create(
            model=self.vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            return []

        try:
            data = json.loads(content)
            # Handle both {"claims": [...]} and [...] formats
            if isinstance(data, list):
                return data
            return data.get("claims", [])
        except json.JSONDecodeError:
            return []

    async def generate_cards(
        self,
        claims: list[Claim],
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Generate flashcard drafts from claims."""
        response = await self.client.chat.completions.create(
            model=self.text_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at creating effective Anki flashcards. "
                    "Output valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            return []

        try:
            data = json.loads(content)
            if isinstance(data, list):
                return data
            return data.get("cards", [])
        except json.JSONDecodeError:
            return []

    async def critique_cards(
        self,
        cards: list[CardDraft],
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Critique flashcard drafts."""
        response = await self.client.chat.completions.create(
            model=self.text_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at evaluating Anki flashcard quality. "
                    "Output valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            return []

        try:
            data = json.loads(content)
            if isinstance(data, list):
                return data
            return data.get("critiques", [])
        except json.JSONDecodeError:
            return []
