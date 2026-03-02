"""
verbum/api/server.py
====================
API REST opcional para o verbumAI.

Instalação das dependências extras:
    pip install -e ".[api]"

Execução:
    uvicorn verbum.api.server:app --reload --port 8000
    # ou via Makefile:
    make serve

Documentação interativa: http://localhost:8000/docs
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from verbum import __version__
from verbum.config import cfg
from verbum.pipeline import QueryResult, ask as pipeline_ask
from verbum.retriever import preload

# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="verbumAI API",
    description="Busca semântica na Bíblia usando RAG — sem alucinação",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ProviderEnum(str, Enum):
    claude = "claude"
    openai = "openai"
    ollama = "ollama"


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Tema ou pergunta a consultar na Bíblia")
    provider: Optional[ProviderEnum] = Field(None, description="Provider LLM (padrão: .env)")
    top_k: int = Field(cfg.top_k_context, ge=1, le=30, description="Versículos no contexto")


class VerseOut(BaseModel):
    reference: str
    book: str
    chapter: int
    verse: int
    text: str
    similarity: float


class QueryResponse(BaseModel):
    query: str
    provider: str
    total_verses: int
    verses: list[VerseOut]
    answer: str


# ─── Lifecycle ───────────────────────────────────────────────────────────────

@app.on_event("startup")
async def _startup():
    preload()


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health", tags=["Infra"])
async def health():
    """Verifica se a API está operacional."""
    return {"status": "ok", "version": __version__}


@app.get("/stats", tags=["Infra"])
async def stats():
    """Estatísticas do banco vetorial."""
    import chromadb

    client = chromadb.PersistentClient(path=str(cfg.db_path))
    col = client.get_collection(cfg.collection_name)
    return {
        "total_verses": col.count(),
        "collection": cfg.collection_name,
        "embedding_model": cfg.embedding_model,
        "providers": ["claude", "openai", "ollama"],
    }


@app.post("/query", response_model=QueryResponse, tags=["RAG"])
async def query_bible(req: QueryRequest):
    """
    Consulta a Bíblia por tema usando busca semântica + LLM.

    - **query**: Tema ou pergunta em linguagem natural
    - **provider**: claude | openai | ollama (padrão: configurado no .env)
    - **top_k**: Quantos versículos usar como contexto (1–30)
    """
    try:
        result: QueryResult = pipeline_ask(
            req.query,
            provider=req.provider.value if req.provider else None,
            top_k_context=req.top_k,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return QueryResponse(
        query=result.query,
        provider=result.provider_name,
        total_verses=result.total_verses,
        verses=[
            VerseOut(
                reference=v.reference,
                book=v.book,
                chapter=v.chapter,
                verse=v.verse,
                text=v.text,
                similarity=v.similarity,
            )
            for v in result.verses
        ],
        answer=result.answer,
    )
