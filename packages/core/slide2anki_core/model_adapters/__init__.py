"""Model adapters for different LLM backends.

Supported providers:
- OpenAI: GPT-5.x series (gpt-5.2, gpt-5.1, gpt-5, gpt-5-mini, gpt-5-nano)
- Google: Gemini 3 series (gemini-3-pro-preview, gemini-3-flash-preview)
- xAI: Grok 4.x series (grok-4-1-fast, grok-4-fast)
- Ollama: Local models via OllamaAdapter (uses OpenAI-compatible API)
"""

from slide2anki_core.model_adapters.base import BaseModelAdapter
from slide2anki_core.model_adapters.google import GoogleAdapter
from slide2anki_core.model_adapters.openai import OpenAIAdapter
from slide2anki_core.model_adapters.xai import XAIAdapter

__all__ = ["BaseModelAdapter", "GoogleAdapter", "OpenAIAdapter", "XAIAdapter"]
