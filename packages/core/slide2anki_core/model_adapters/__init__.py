"""Model adapters for different LLM backends."""

from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.model_adapters.openai import OpenAIAdapter

__all__ = ["BaseModelAdapter", "OpenAIAdapter"]
