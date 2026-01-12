"""OpenAI model adapter."""

import asyncio
import base64
import json
from typing import Any

from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim
from slide2anki_core.utils.logging import get_logger
from slide2anki_core.utils.retry import with_retry

logger = get_logger(__name__)

# Default timeout for API calls (seconds)
DEFAULT_TIMEOUT = 120.0


def _parse_json_response(content: str) -> dict[str, Any] | list[dict[str, Any]]:
    """Parse JSON content returned by the model.

    Args:
        content: Raw response content string

    Returns:
        Parsed JSON payload (dict or list), empty list on failure
    """
    if not content:
        logger.warning("Empty response content received")
        return []

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}. Content: {content[:200]}...")
        return []


class OpenAIAdapter(BaseModelAdapter):
    """Adapter for OpenAI models (GPT-4 Vision, GPT-4)."""

    def __init__(
        self,
        api_key: str,
        vision_model: str = "gpt-4o",
        text_model: str = "gpt-4o",
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ):
        """Initialize the OpenAI adapter.

        Args:
            api_key: OpenAI API key
            vision_model: Model for vision tasks
            text_model: Model for text tasks
            base_url: Optional custom base URL
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for transient failures
        """
        self.api_key = api_key
        self.vision_model = vision_model
        self.text_model = text_model
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

        self._client: Any = None
        logger.info(
            f"Initialized OpenAI adapter (vision={vision_model}, text={text_model})"
        )

    @property
    def client(self) -> Any:
        """Lazy-load the OpenAI client."""
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def _call_api(
        self,
        model: str,
        messages: list[dict[str, Any]],
        operation_name: str,
    ) -> str:
        """Call the OpenAI API with retry logic.

        Args:
            model: Model to use
            messages: Chat messages
            operation_name: Name for logging

        Returns:
            Response content string
        """

        async def _make_request() -> str:
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=4096,
                    response_format={"type": "json_object"},
                ),
                timeout=self.timeout,
            )
            return response.choices[0].message.content or ""

        logger.debug(f"Starting {operation_name} with model {model}")
        result = await with_retry(
            _make_request,
            max_attempts=self.max_retries,
            operation_name=operation_name,
        )
        logger.debug(f"Completed {operation_name}")
        return result

    async def extract_claims(
        self,
        image_data: bytes,
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Extract claims from a slide image using vision model."""
        # Encode image as base64
        image_b64 = base64.b64encode(image_data).decode("utf-8")
        logger.info(f"Extracting claims from image ({len(image_data)} bytes)")

        messages = [
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
        ]

        content = await self._call_api(
            model=self.vision_model,
            messages=messages,
            operation_name="extract_claims",
        )

        data = _parse_json_response(content)
        if isinstance(data, list):
            logger.info(f"Extracted {len(data)} claims")
            return data
        if isinstance(data, dict):
            claims = data.get("claims", [])
            logger.info(f"Extracted {len(claims)} claims")
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
        messages: list[dict[str, Any]] = []
        if image_data:
            image_b64 = base64.b64encode(image_data).decode("utf-8")
            messages.append(
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
            )
            model = self.vision_model
            logger.debug("Using vision model for structured generation")
        else:
            messages.append({"role": "user", "content": prompt})
            model = self.text_model
            logger.debug("Using text model for structured generation")

        content = await self._call_api(
            model=model,
            messages=messages,
            operation_name="generate_structured",
        )

        return _parse_json_response(content)

    async def generate_cards(
        self,
        claims: list[Claim],
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Generate flashcard drafts from claims."""
        logger.info(f"Generating cards from {len(claims)} claims")

        messages = [
            {
                "role": "system",
                "content": "You are an expert at creating effective Anki flashcards. "
                "Output valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ]

        content = await self._call_api(
            model=self.text_model,
            messages=messages,
            operation_name="generate_cards",
        )

        data = _parse_json_response(content)
        if isinstance(data, list):
            logger.info(f"Generated {len(data)} cards")
            return data
        if isinstance(data, dict):
            cards = data.get("cards", [])
            logger.info(f"Generated {len(cards)} cards")
            return cards
        return []

    async def critique_cards(
        self,
        cards: list[CardDraft],
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Critique flashcard drafts."""
        logger.info(f"Critiquing {len(cards)} cards")

        messages = [
            {
                "role": "system",
                "content": "You are an expert at evaluating Anki flashcard quality. "
                "Output valid JSON only.",
            },
            {"role": "user", "content": prompt},
        ]

        content = await self._call_api(
            model=self.text_model,
            messages=messages,
            operation_name="critique_cards",
        )

        data = _parse_json_response(content)
        if isinstance(data, list):
            logger.info(f"Received {len(data)} critiques")
            return data
        if isinstance(data, dict):
            critiques = data.get("critiques", [])
            logger.info(f"Received {len(critiques)} critiques")
            return critiques
        return []
