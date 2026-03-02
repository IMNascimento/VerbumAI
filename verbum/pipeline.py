"""
verbum/pipeline.py
==================
Orquestra o pipeline RAG completo:
  Retrieval -> Context -> LLM -> Response
"""

from __future__ import annotations

from dataclasses import dataclass

from verbum import retriever
from verbum.config import cfg
from verbum.prompts import SYSTEM, build_context_block, build_user_prompt
from verbum.providers import get_provider
from verbum.retriever import SearchResult


@dataclass
class QueryResult:
    """Resultado completo de uma consulta ao verbumAI."""

    query: str
    provider_name: str
    verses: list[SearchResult]
    answer: str

    @property
    def total_verses(self) -> int:
        return len(self.verses)


def ask(
    query: str,
    *,
    provider: str | None = None,
    top_k_context: int | None = None,
    top_k_retrieval: int | None = None,
) -> QueryResult:
    """
    Pipeline principal do verbumAI.

    Args:
        query: Tema ou pergunta em linguagem natural.
        provider: Provider a usar ('claude', 'openai', 'ollama').
                  Se None, usa cfg.provider.
        top_k_context: Versículos enviados ao LLM (janela de contexto).
        top_k_retrieval: Versículos buscados antes de filtrar.

    Returns:
        QueryResult com versículos e resposta do LLM.
    """
    provider_name = cfg.validate_provider(provider)
    k_retrieval = top_k_retrieval or cfg.top_k_retrieval
    k_context = top_k_context or cfg.top_k_context

    # ── 1. Retrieval semântico ────────────────────────────────────────────────
    results = retriever.search(query, top_k=k_retrieval)
    context_verses = results[:k_context]

    # ── 2. Montagem do contexto ──────────────────────────────────────────────
    context_block = build_context_block(context_verses)
    user_prompt = build_user_prompt(query, context_block)

    # ── 3. Geração via LLM ───────────────────────────────────────────────────
    llm = get_provider(provider_name)
    answer = llm.complete(SYSTEM, user_prompt)

    return QueryResult(
        query=query,
        provider_name=llm.name,
        verses=context_verses,
        answer=answer,
    )
