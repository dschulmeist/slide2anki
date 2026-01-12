"""Ollama model adapter for local inference."""

import asyncio
import base64
import json
import re
from typing import Any

from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim
from slide2anki_core.utils.logging import get_logger
from slide2anki_core.utils.retry import with_retry

logger = get_logger(__name__)

# Default timeout for API calls (seconds)
DEFAULT_TIMEOUT = 180.0  # Ollama can be slower than cloud APIs


def _parse_json_response(content: str) -> dict[str, Any] | list[dict[str, Any]]:
    """Parse JSON content returned by the model.

    Args:
        content: Raw response content string

    Returns:
        Parsed JSON payload (dict or list), empty list on failure
    """
    if not content:
        logger.warning("Empty response content received from Ollama")
        return []

    # Try direct JSON parsing first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code blocks or surrounding text
    logger.debug("Direct JSON parse failed, attempting extraction")
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Last resort: find any JSON object or array
    match = re.search(r"(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\])", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    logger.error(f"Failed to parse JSON from Ollama response: {content[:200]}...")
    return []


class OllamaAdapter(BaseModelAdapter):
    """Adapter for Ollama local models."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        vision_model: str = "llava",
        text_model: str = "llama3",
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ):
        """Initialize the Ollama adapter.

        Args:
            base_url: Ollama server URL
            vision_model: Model for vision tasks (e.g., llava)
            text_model: Model for text tasks (e.g., llama3)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for transient failures
        """
        self.base_url = base_url.rstrip("/")
        self.vision_model = vision_model
        self.text_model = text_model
        self.timeout = timeout
        self.max_retries = max_retries

        self._client: Any = None
        logger.info(
            f"Initialized Ollama adapter (url={base_url}, vision={vision_model}, text={text_model})"
        )

    @property
    def client(self) -> Any:
        """Lazy-load the HTTP client."""
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def _generate(
        self,
        model: str,
        prompt: str,
        images: list[str] | None = None,
        operation_name: str = "generate",
    ) -> str:
        """Call Ollama generate API with retry logic.

        Args:
            model: Model name
            prompt: Text prompt
            images: Optional list of base64-encoded images
            operation_name: Name for logging

        Returns:
            Generated text response
        """
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if images:
            payload["images"] = images

        async def _make_request() -> str:
            logger.debug(f"Calling Ollama {operation_name} with model {model}")
            response = await asyncio.wait_for(
                self.client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                ),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

        result = await with_retry(
            _make_request,
            max_attempts=self.max_retries,
            operation_name=f"ollama_{operation_name}",
        )
        logger.debug(f"Completed Ollama {operation_name}")
        return result

    async def extract_claims(
        self,
        image_data: bytes,
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Extract claims from a slide image using vision model."""
        # Encode image as base64
        image_b64 = base64.b64encode(image_data).decode("utf-8")
        logger.info(f"Extracting claims from image ({len(image_data)} bytes) via Ollama")

        # Add JSON instruction to prompt
        full_prompt = f"{prompt}\n\nRespond with a valid JSON array only. No additional text."

        response = await self._generate(
            model=self.vision_model,
            prompt=full_prompt,
            images=[image_b64],
            operation_name="extract_claims",
        )

        data = _parse_json_response(response)
        if isinstance(data, list):
            logger.info(f"Extracted {len(data)} claims via Ollama")
            return data
        if isinstance(data, dict):
            claims = data.get("claims", [])
            logger.info(f"Extracted {len(claims)} claims via Ollama")
            return claims
        return []

    async def generate_structured(
        self,
        prompt: str,
        image_data: bytes | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Generate structured JSON using the selected model.

        Args:
            prompt: Prompt that specifies the JSON output format
            image_data: Optional image bytes for vision calls

        Returns:
            Parsed JSON payload (dict or list)
        """
        full_prompt = f"{prompt}\n\nRespond with valid JSON only. No additional text."
        images = None
        model = self.text_model
        if image_data:
            model = self.vision_model
            images = [base64.b64encode(image_data).decode("utf-8")]
            logger.debug("Using vision model for structured generation via Ollama")
        else:
            logger.debug("Using text model for structured generation via Ollama")

        response = await self._generate(
            model=model,
            prompt=full_prompt,
            images=images,
            operation_name="generate_structured",
        )

        return _parse_json_response(response)

    async def generate_cards(
        self,
        claims: list[Claim],
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Generate flashcard drafts from claims."""
        logger.info(f"Generating cards from {len(claims)} claims via Ollama")
        full_prompt = f"{prompt}\n\nRespond with a valid JSON array only. No additional text."

        response = await self._generate(
            model=self.text_model,
            prompt=full_prompt,
            operation_name="generate_cards",
        )

        data = _parse_json_response(response)
        if isinstance(data, list):
            logger.info(f"Generated {len(data)} cards via Ollama")
            return data
        if isinstance(data, dict):
            cards = data.get("cards", [])
            logger.info(f"Generated {len(cards)} cards via Ollama")
            return cards
        return []

    async def critique_cards(
        self,
        cards: list[CardDraft],
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Critique flashcard drafts."""
        logger.info(f"Critiquing {len(cards)} cards via Ollama")
        full_prompt = f"{prompt}\n\nRespond with a valid JSON array only. No additional text."

        response = await self._generate(
            model=self.text_model,
            prompt=full_prompt,
            operation_name="critique_cards",
        )

        data = _parse_json_response(response)
        if isinstance(data, list):
            logger.info(f"Received {len(data)} critiques via Ollama")
            return data
        if isinstance(data, dict):
            critiques = data.get("critiques", [])
            logger.info(f"Received {len(critiques)} critiques via Ollama")
            return critiques
        return []

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.debug("Closed Ollama HTTP client")
