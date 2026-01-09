"""Ollama model adapter for local inference."""

import base64
import json
from typing import Any, Optional

from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim


class OllamaAdapter(BaseModelAdapter):
    """Adapter for Ollama local models."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        vision_model: str = "llava",
        text_model: str = "llama3",
    ):
        """Initialize the Ollama adapter.

        Args:
            base_url: Ollama server URL
            vision_model: Model for vision tasks (e.g., llava)
            text_model: Model for text tasks (e.g., llama3)
        """
        self.base_url = base_url.rstrip("/")
        self.vision_model = vision_model
        self.text_model = text_model

        self._client: Any = None

    @property
    def client(self) -> Any:
        """Lazy-load the HTTP client."""
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def _generate(
        self,
        model: str,
        prompt: str,
        images: Optional[list[str]] = None,
    ) -> str:
        """Call Ollama generate API."""
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if images:
            payload["images"] = images

        response = await self.client.post(
            f"{self.base_url}/api/generate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")

    async def extract_claims(
        self,
        image_data: bytes,
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Extract claims from a slide image using vision model."""
        # Encode image as base64
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        # Add JSON instruction to prompt
        full_prompt = f"{prompt}\n\nRespond with a valid JSON array only."

        response = await self._generate(
            model=self.vision_model,
            prompt=full_prompt,
            images=[image_b64],
        )

        try:
            # Try to extract JSON from response
            data = json.loads(response)
            if isinstance(data, list):
                return data
            return data.get("claims", [])
        except json.JSONDecodeError:
            # Try to find JSON array in response
            import re

            match = re.search(r"\[.*\]", response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return []

    async def generate_cards(
        self,
        claims: list[Claim],
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Generate flashcard drafts from claims."""
        full_prompt = f"{prompt}\n\nRespond with a valid JSON array only."

        response = await self._generate(
            model=self.text_model,
            prompt=full_prompt,
        )

        try:
            data = json.loads(response)
            if isinstance(data, list):
                return data
            return data.get("cards", [])
        except json.JSONDecodeError:
            import re

            match = re.search(r"\[.*\]", response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return []

    async def critique_cards(
        self,
        cards: list[CardDraft],
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Critique flashcard drafts."""
        full_prompt = f"{prompt}\n\nRespond with a valid JSON array only."

        response = await self._generate(
            model=self.text_model,
            prompt=full_prompt,
        )

        try:
            data = json.loads(response)
            if isinstance(data, list):
                return data
            return data.get("critiques", [])
        except json.JSONDecodeError:
            import re

            match = re.search(r"\[.*\]", response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return []
