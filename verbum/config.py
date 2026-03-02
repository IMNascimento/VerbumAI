"""
verbum/config.py
================
Configuração centralizada lida do .env.
Único ponto de verdade para todos os parâmetros do sistema.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Carrega .env na raiz do projeto (sobe a árvore até encontrar)
_root = Path(__file__).parent.parent
load_dotenv(_root / ".env", override=False)


@dataclass(frozen=True)
class Config:
    # ── Provider ─────────────────────────────────────────────────────────────
    provider: str = field(default_factory=lambda: os.getenv("VERBUM_PROVIDER", "claude"))

    # ── Modelos ──────────────────────────────────────────────────────────────
    claude_model: str = field(
        default_factory=lambda: os.getenv("VERBUM_CLAUDE_MODEL", "claude-opus-4-6")
    )
    openai_model: str = field(
        default_factory=lambda: os.getenv("VERBUM_OPENAI_MODEL", "gpt-4o")
    )
    ollama_model: str = field(
        default_factory=lambda: os.getenv("VERBUM_OLLAMA_MODEL", "llama3.2")
    )
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("VERBUM_OLLAMA_BASE_URL", "http://localhost:11434")
    )

    # ── Embedding ────────────────────────────────────────────────────────────
    embedding_model: str = field(
        default_factory=lambda: os.getenv(
            "VERBUM_EMBEDDING_MODEL", "paraphrase-multilingual-mpnet-base-v2"
        )
    )

    # ── RAG ──────────────────────────────────────────────────────────────────
    top_k_retrieval: int = field(
        default_factory=lambda: int(os.getenv("VERBUM_TOP_K_RETRIEVAL", "20"))
    )
    top_k_context: int = field(
        default_factory=lambda: int(os.getenv("VERBUM_TOP_K_CONTEXT", "8"))
    )

    # ── Paths ─────────────────────────────────────────────────────────────────
    db_path: Path = field(
        default_factory=lambda: Path(os.getenv("VERBUM_DB_PATH", "data/chroma_db"))
    )
    bible_path: Path = field(
        default_factory=lambda: Path(os.getenv("VERBUM_BIBLE_PATH", "data/bible_acf.json"))
    )

    # ── Constantes ────────────────────────────────────────────────────────────
    bible_url: str = (
        "https://raw.githubusercontent.com/thiagobodruk/biblia/master/json/acf.json"
    )
    collection_name: str = "bible_verses"

    def active_model_name(self) -> str:
        """Retorna o nome do modelo ativo conforme o provider configurado."""
        return {
            "claude": self.claude_model,
            "openai": self.openai_model,
            "ollama": self.ollama_model,
        }.get(self.provider, self.provider)

    def validate_provider(self, provider: str | None = None) -> str:
        """Valida e retorna o provider, usando o padrão se None."""
        p = provider or self.provider
        valid = {"claude", "openai", "ollama"}
        if p not in valid:
            raise ValueError(f"Provider '{p}' inválido. Use: {valid}")
        return p


# Singleton global — importe de qualquer módulo
cfg = Config()
