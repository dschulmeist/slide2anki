"""Base model adapter interface."""

from abc import ABC, abstractmethod
from typing import Any

from slide2anki_core.schemas.cards import CardDraft
from slide2anki_core.schemas.claims import Claim


class BaseModelAdapter(ABC):
    """Abstract base class for model adapters."""

    @abstractmethod
    async def extract_claims(
        self,
        image_data: bytes,
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Extract claims from a slide image.

        Args:
            image_data: PNG image bytes
            prompt: Extraction prompt

        Returns:
            List of claim dictionaries
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        image_data: bytes | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Generate structured JSON from a model call.

        Args:
            prompt: Prompt that specifies the JSON output format
            image_data: Optional image bytes for vision calls

        Returns:
            Parsed JSON data (dict or list)
        """
        pass

    @abstractmethod
    async def generate_cards(
        self,
        claims: list[Claim],
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Generate flashcard drafts from claims.

        Args:
            claims: List of extracted claims
            prompt: Generation prompt

        Returns:
            List of card dictionaries
        """
        pass

    @abstractmethod
    async def critique_cards(
        self,
        cards: list[CardDraft],
        prompt: str,
    ) -> list[dict[str, Any]]:
        """Critique flashcard drafts.

        Args:
            cards: List of card drafts
            prompt: Critique prompt

        Returns:
            List of critique dictionaries
        """
        pass
