from __future__ import annotations

from verbum.config import cfg
from verbum.providers.base import BaseProvider
from verbum.providers.ollama import OllamaProvider
from verbum.providers.openai_ import OpenAIProvider
from verbum.providers.claude import ClaudeProvider


def get_provider(name: str | None = None) -> BaseProvider:
    """
    Retorna o provider configurado.
    name: "ollama" | "openai" | "claude" (opcional; se None usa cfg.provider)
    """
    provider = (name or getattr(cfg, "provider", None) or "ollama").lower().strip()

    if provider in ("ollama",):
        return OllamaProvider()

    if provider in ("openai", "gpt"):
        return OpenAIProvider()

    if provider in ("claude", "anthropic"):
        return ClaudeProvider()

    raise ValueError(f"Provider inválido: {provider}")