"""
verbum/providers/claude.py
==========================
Provider para a API da Anthropic (Claude).
"""

import os

from verbum.config import cfg
from verbum.providers.base import BaseProvider


class ClaudeProvider(BaseProvider):
    @property
    def name(self) -> str:
        return f"Claude · {cfg.claude_model}"

    def complete(self, system: str, user: str) -> str:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY não encontrada.\n"
                "Adicione-a ao seu .env ou exporte como variável de ambiente."
            )

        import anthropic  # import tardio — só instala se usar este provider

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=cfg.claude_model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text
