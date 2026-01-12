"""Google Gemini model adapter."""

import asyncio
import base64
import json
from typing import Any

from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim
from slide2anki_core.utils.logging import get_logger
from slide2anki_core.utils.retry import RateLimitError, with_retry

logger = get_logger(__name__)


def _wrap_google_error(e: Exception) -> Exception:
    """Convert Google API errors to standard exceptions for retry handling.

    Args:
        e: Original exception from Google API

    Returns:
        Wrapped exception (RateLimitError for rate limits, original otherwise)
    """
    error_str = str(e).lower()
    error_type = type(e).__name__

    # Check for rate limit / quota errors
    if any(
        indicator in error_str
        for indicator in [
            "resource exhausted",
            "quota",
            "rate limit",
            "429",
            "too many requests",
        ]
    ) or error_type in ("ResourceExhausted", "TooManyRequests"):
        return RateLimitError(f"Google API rate limit: {e}")

    # Check for retryable server errors
    if any(
        indicator in error_str
        for indicator in ["503", "500", "internal", "unavailable", "deadline"]
    ) or error_type in (
        "ServiceUnavailable",
        "InternalServerError",
        "DeadlineExceeded",
    ):
        return ConnectionError(f"Google API server error: {e}")

    return e


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

    # Try to extract JSON from markdown code blocks if present
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        if len(lines) >= 2:
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}. Content: {content[:200]}...")
        return []


class GoogleAdapter(BaseModelAdapter):
    """Adapter for Google Gemini models."""

    def __init__(
        self,
        api_key: str,
        vision_model: str = "gemini-2.5-flash",
        text_model: str = "gemini-2.5-flash",
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ):
        """Initialize the Google Gemini adapter.

        Args:
            api_key: Google AI API key
            vision_model: Model for vision tasks
            text_model: Model for text tasks
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for transient failures
        """
        self.api_key = api_key
        self.vision_model = vision_model
        self.text_model = text_model
        self.timeout = timeout
        self.max_retries = max_retries

        self._client: Any = None
        logger.info(
            f"Initialized Google adapter (vision={vision_model}, text={text_model})"
        )

    @property
    def client(self) -> Any:
        """Lazy-load the Google Generative AI client."""
        if self._client is None:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            self._client = genai
        return self._client

    async def _call_api(
        self,
        model: str,
        contents: list[Any],
        operation_name: str,
        system_instruction: str | None = None,
    ) -> str:
        """Call the Google Generative AI API with retry logic.

        Args:
            model: Model to use
            contents: Content parts for the request
            operation_name: Name for logging
            system_instruction: Optional system instruction

        Returns:
            Response content string
        """

        async def _make_request() -> str:
            """Make a single request to the Gemini API."""
            try:
                model_instance = self.client.GenerativeModel(
                    model_name=model,
                    system_instruction=system_instruction,
                    generation_config={
                        "response_mime_type": "application/json",
                    },
                )
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        model_instance.generate_content,
                        contents,
                    ),
                    timeout=self.timeout,
                )
                # Safely extract text from response - handle empty/blocked responses
                if not response.candidates:
                    logger.warning(f"{operation_name}: No candidates in response")
                    return ""
                candidate = response.candidates[0]
                # Check finish_reason: 1=STOP (normal), 2=MAX_TOKENS, 3=SAFETY, 4=RECITATION, 5=OTHER
                finish_reason = getattr(candidate, "finish_reason", None)
                if finish_reason and finish_reason != 1:
                    logger.warning(
                        f"{operation_name}: Response finished with reason {finish_reason}"
                    )
                if not candidate.content or not candidate.content.parts:
                    logger.warning(
                        f"{operation_name}: No content parts in response (finish_reason={finish_reason})"
                    )
                    return ""
                # Extract text from parts
                text_parts = [
                    part.text
                    for part in candidate.content.parts
                    if hasattr(part, "text")
                ]
                return "".join(text_parts)
            except Exception as e:
                # Wrap Google-specific errors for proper retry handling
                raise _wrap_google_error(e) from e

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
        logger.info(f"Extracting claims from image ({len(image_data)} bytes)")

        # Create image part for Gemini
        image_part = {
            "mime_type": "image/png",
            "data": base64.b64encode(image_data).decode("utf-8"),
        }

        contents = [
            prompt,
            image_part,
        ]

        content = await self._call_api(
            model=self.vision_model,
            contents=contents,
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
        contents: list[Any] = []
        if image_data:
            image_part = {
                "mime_type": "image/png",
                "data": base64.b64encode(image_data).decode("utf-8"),
            }
            contents = [prompt, image_part]
            model = self.vision_model
            logger.debug("Using vision model for structured generation")
        else:
            contents = [prompt]
            model = self.text_model
            logger.debug("Using text model for structured generation")

        content = await self._call_api(
            model=model,
            contents=contents,
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

        content = await self._call_api(
            model=self.text_model,
            contents=[prompt],
            operation_name="generate_cards",
            system_instruction="You are an expert at creating effective Anki flashcards. Output valid JSON only.",
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

        content = await self._call_api(
            model=self.text_model,
            contents=[prompt],
            operation_name="critique_cards",
            system_instruction="You are an expert at evaluating Anki flashcard quality. Output valid JSON only.",
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
