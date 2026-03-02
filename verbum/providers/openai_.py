"""
verbum/providers/openai_.py
===========================
Provider para a API da OpenAI (GPT).
"""

import os

from verbum.config import cfg
from verbum.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    @property
    def name(self) -> str:
        return f"OpenAI · {cfg.openai_model}"

    def complete(self, system: str, user: str) -> str:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY não encontrada.\n"
                "Adicione-a ao seu .env ou exporte como variável de ambiente."
            )

        from openai import OpenAI  # import tardio

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=cfg.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=2048,
            temperature=0.1,
        )
        return response.choices[0].message.content
