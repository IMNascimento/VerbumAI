"""
verbum/providers/ollama.py
==========================
Provider para modelos locais via Ollama.
Requer: ollama serve (rodando localmente).
"""

from verbum.config import cfg
from verbum.providers.base import BaseProvider


class OllamaProvider(BaseProvider):
    @property
    def name(self) -> str:
        return f"Ollama · {cfg.ollama_model}"

    def complete(self, system: str, user: str) -> str:
        import requests  # import tardio

        url = f"{cfg.ollama_base_url}/api/chat"
        payload = {
            "model": cfg.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        }

        try:
            response = requests.post(url, json=payload, timeout=180)
            response.raise_for_status()
            return response.json()["message"]["content"]
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                f"Não foi possível conectar ao Ollama em {cfg.ollama_base_url}.\n"
                "Verifique se o Ollama está rodando: ollama serve\n"
                f"E se o modelo está instalado: ollama pull {cfg.ollama_model}"
            )
