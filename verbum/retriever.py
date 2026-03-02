"""
verbum/retriever.py
===================
Motor de busca semântica: converte a query em embedding
e recupera os versículos mais próximos no ChromaDB.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from functools import lru_cache

import chromadb
from sentence_transformers import SentenceTransformer

from verbum.config import cfg


@dataclass
class SearchResult:
    """Um versículo recuperado com seu score de similaridade."""

    reference: str
    book: str
    chapter: int
    verse: int
    text: str
    full_text: str
    similarity: float

    def __str__(self) -> str:
        return f"{self.reference} — {self.text}"


# ─── Singleton de recursos pesados ───────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_model() -> SentenceTransformer:
    return SentenceTransformer(cfg.embedding_model)


@lru_cache(maxsize=1)
def _load_collection():
    if not cfg.db_path.exists():
        print(
            "\n Banco vetorial não encontrado.\n"
            "   Execute primeiro: verbum setup\n"
            "   Ou: make setup\n"
        )
        sys.exit(1)

    client = chromadb.PersistentClient(path=str(cfg.db_path))
    return client.get_collection(cfg.collection_name)


# ─── API pública ─────────────────────────────────────────────────────────────

def search(query: str, top_k: int | None = None) -> list[SearchResult]:
    """
    Busca semântica: retorna os versículos mais relevantes para a query.

    Args:
        query: Tema ou pergunta em linguagem natural.
        top_k: Número de resultados. Usa cfg.top_k_retrieval se None.

    Returns:
        Lista de SearchResult ordenada por similaridade decrescente.
    """
    k = top_k or cfg.top_k_retrieval
    model = _load_model()
    collection = _load_collection()

    embedding = model.encode(query).tolist()
    k = min(k, collection.count())

    results = collection.query(
        query_embeddings=[embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    return [
        SearchResult(
            reference=meta["reference"],
            book=meta["book"],
            chapter=meta["chapter"],
            verse=meta["verse"],
            text=meta["text"],
            full_text=doc,
            similarity=round(1 - dist, 4),
        )
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ]


def preload() -> None:
    """Pré-carrega o modelo e a coleção (útil na inicialização da API/CLI)."""
    _load_model()
    _load_collection()
