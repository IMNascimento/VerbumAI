"""
verbum/indexer.py
=================
Responsável por:
  1. Baixar a Bíblia ACF (domínio público) em JSON
  2. Parsear cada versículo com metadados completos
  3. Gerar embeddings e indexar no ChromaDB
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import chromadb
import requests
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from verbum.config import cfg

# Batch size para inserção em lote
_BATCH_SIZE = 256

# Nomes completos dos livros (chave = abreviação em minúsculo do JSON)
_BOOK_NAMES: dict[str, str] = {
    "gn": "Gênesis", "ex": "Êxodo", "lv": "Levítico", "nm": "Números",
    "dt": "Deuteronômio", "js": "Josué", "jz": "Juízes", "rt": "Rute",
    "1sm": "1 Samuel", "2sm": "2 Samuel", "1rs": "1 Reis", "2rs": "2 Reis",
    "1cr": "1 Crônicas", "2cr": "2 Crônicas", "ed": "Esdras", "ne": "Neemias",
    "et": "Ester", "jó": "Jó", "sl": "Salmos", "pv": "Provérbios",
    "ec": "Eclesiastes", "ct": "Cânticos", "is": "Isaías", "jr": "Jeremias",
    "lm": "Lamentações", "ez": "Ezequiel", "dn": "Daniel", "os": "Oséias",
    "jl": "Joel", "am": "Amós", "ob": "Obadias", "jn": "Jonas",
    "mq": "Miquéias", "na": "Naum", "hc": "Habacuque", "sf": "Sofonias",
    "ag": "Ageu", "zc": "Zacarias", "ml": "Malaquias",
    "mt": "Mateus", "mc": "Marcos", "lc": "Lucas", "jo": "João",
    "at": "Atos", "rm": "Romanos", "1co": "1 Coríntios", "2co": "2 Coríntios",
    "gl": "Gálatas", "ef": "Efésios", "fp": "Filipenses", "cl": "Colossenses",
    "1ts": "1 Tessalonicenses", "2ts": "2 Tessalonicenses",
    "1tm": "1 Timóteo", "2tm": "2 Timóteo", "tt": "Tito", "fm": "Filemom",
    "hb": "Hebreus", "tg": "Tiago", "1pe": "1 Pedro", "2pe": "2 Pedro",
    "1jo": "1 João", "2jo": "2 João", "3jo": "3 João", "jd": "Judas",
    "ap": "Apocalipse",
}


# ─── Tipos ───────────────────────────────────────────────────────────────────

class Verse:
    """Representa um versículo com todos os metadados necessários."""

    __slots__ = ("id", "text", "book", "book_abbr", "chapter", "verse", "reference", "full_text")

    def __init__(
        self,
        *,
        book_abbr: str,
        book: str,
        chapter: int,
        verse: int,
        text: str,
    ) -> None:
        self.book_abbr = book_abbr.upper()
        self.book = book
        self.chapter = chapter
        self.verse = verse
        self.text = text
        self.reference = f"{book} {chapter}:{verse}"
        self.id = f"{book_abbr.lower()}_{chapter}_{verse}"
        self.full_text = f"{self.reference} — {text}"

    def to_metadata(self) -> dict:
        return {
            "book": self.book,
            "book_abbr": self.book_abbr,
            "chapter": self.chapter,
            "verse": self.verse,
            "reference": self.reference,
            "text": self.text,
        }


# ─── Download ────────────────────────────────────────────────────────────────

def download_bible(*, force: bool = False) -> list:
    """
    Baixa a Bíblia ACF em JSON e salva em disco.
    Retorna o conteúdo já parseado como lista.
    """
    path: Path = cfg.bible_path
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists() and not force:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    response = requests.get(cfg.bible_url, timeout=60)
    response.raise_for_status()
    text = response.content.decode("utf-8-sig")
    data = json.loads(text)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return data


# ─── Parser ──────────────────────────────────────────────────────────────────

def parse_verses(raw: list) -> list[Verse]:
    """Converte o JSON bruto da Bíblia em objetos Verse."""
    verses: list[Verse] = []

    for book_data in raw:
        abbr = book_data.get("abbrev", "").lower()
        name = book_data.get("name") or _BOOK_NAMES.get(abbr, abbr.upper())

        for chap_idx, chapter in enumerate(book_data.get("chapters", []), start=1):
            for verse_idx, verse_text in enumerate(chapter, start=1):
                verses.append(
                    Verse(
                        book_abbr=abbr,
                        book=name,
                        chapter=chap_idx,
                        verse=verse_idx,
                        text=str(verse_text),
                    )
                )

    return verses


def _batched(items: list, size: int) -> Iterator[list]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


# ─── Indexação ───────────────────────────────────────────────────────────────

def build_index(verses: list[Verse], *, force: bool = False) -> None:
    """
    Gera embeddings e indexa os versículos no ChromaDB.
    Se o índice já existir e force=False, pula a indexação.
    """
    db_path = str(cfg.db_path)
    cfg.db_path.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=db_path)

    # Verifica se já foi indexado
    existing = client.list_collections()
    if any(c.name == cfg.collection_name for c in existing) and not force:
        col = client.get_collection(cfg.collection_name)
        if col.count() > 0:
            return  # Já indexado

    # Carrega modelo de embedding
    model = SentenceTransformer(cfg.embedding_model)

    # (Re)cria coleção
    try:
        client.delete_collection(cfg.collection_name)
    except Exception:
        pass

    collection = client.create_collection(
        name=cfg.collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    for batch in tqdm(list(_batched(verses, _BATCH_SIZE)), desc="Indexando versículos"):
        texts = [v.full_text for v in batch]
        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        collection.add(
            ids=[v.id for v in batch],
            documents=texts,
            embeddings=embeddings,
            metadatas=[v.to_metadata() for v in batch],
        )


# ─── Entry point para o CLI ──────────────────────────────────────────────────

def run_setup(*, force: bool = False) -> int:
    """
    Fluxo completo de setup: download -> parse -> indexação.
    Retorna o total de versículos indexados.
    """
    raw = download_bible(force=force)
    verses = parse_verses(raw)
    build_index(verses, force=force)
    return len(verses)
