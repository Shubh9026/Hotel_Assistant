from __future__ import annotations

import glob
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


DEFAULT_DOCS_DIR = "data/docs"
DEFAULT_CHROMA_DIR = "data/chroma"
DEFAULT_COLLECTION = "hotel_docs"
DEFAULT_EMBED_MODEL = "all-MiniLM-L6-v2"


@dataclass(frozen=True)
class RagChunk:
    text: str
    metadata: Dict[str, Any]
    distance: Optional[float] = None


def _get_settings() -> Tuple[str, str, str, str]:
    docs_dir = os.getenv("RAG_DOCS_DIR", DEFAULT_DOCS_DIR)
    chroma_dir = os.getenv("RAG_CHROMA_DIR", DEFAULT_CHROMA_DIR)
    collection = os.getenv("RAG_COLLECTION", DEFAULT_COLLECTION)
    embed_model = os.getenv("RAG_EMBED_MODEL", DEFAULT_EMBED_MODEL)
    return docs_dir, chroma_dir, collection, embed_model


def _embedding_function(embed_model: str):
    # Lazy import so the app can still run without RAG deps.
    from chromadb.utils import embedding_functions  # type: ignore

    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=embed_model)


def _client(chroma_dir: str):
    import chromadb  # type: ignore

    Path(chroma_dir).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=chroma_dir)


def get_collection():
    docs_dir, chroma_dir, collection_name, embed_model = _get_settings()
    client = _client(chroma_dir)
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=_embedding_function(embed_model),
        metadata={"docs_dir": docs_dir, "embed_model": embed_model},
    )


def rag_enabled() -> bool:
    """
    RAG is enabled when at least one PDF exists in RAG_DOCS_DIR.
    """
    docs_dir, _, _, _ = _get_settings()
    return bool(glob.glob(str(Path(docs_dir) / "*.pdf")))


def _infer_doc_type(path: str) -> str:
    name = Path(path).name.lower()
    if "menu" in name or "room_service" in name or "room-service" in name:
        return "room_service"
    return "hotel_info"


def _read_pdf_pages(path: str) -> List[str]:
    from pypdf import PdfReader  # type: ignore

    reader = PdfReader(path)
    pages: List[str] = []
    for p in reader.pages:
        try:
            pages.append((p.extract_text() or "").strip())
        except Exception:
            pages.append("")
    return pages


def _chunk_text(text: str, *, chunk_size: int = 1200, overlap: int = 200) -> List[str]:
    """
    Simple char-based chunker to avoid extra deps. Good enough for prototype.
    """
    text = (text or "").strip()
    if not text:
        return []
    if chunk_size <= 0:
        return [text]
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + chunk_size)
        chunks.append(text[start:end].strip())
        if end >= n:
            break
        start = max(0, end - overlap)
    return [c for c in chunks if c]


def build_index(*, force_rebuild: bool = False) -> Dict[str, Any]:
    """
    Ingest PDFs from RAG_DOCS_DIR into a persistent Chroma collection.
    Deterministic ids allow safe re-runs.
    """
    docs_dir, _, _, _ = _get_settings()
    pdfs = sorted(glob.glob(str(Path(docs_dir) / "*.pdf")))
    if not pdfs:
        return {"ok": False, "reason": f"No PDFs found in {docs_dir}"}

    col = get_collection()

    added = 0
    skipped = 0

    for pdf in pdfs:
        doc_type = _infer_doc_type(pdf)
        pages = _read_pdf_pages(pdf)
        for page_idx, page_text in enumerate(pages, start=1):
            for chunk_idx, chunk in enumerate(_chunk_text(page_text), start=1):
                chunk_id = f"{Path(pdf).name}::p{page_idx}::c{chunk_idx}"
                meta = {"source": Path(pdf).name, "page": page_idx, "doc_type": doc_type}

                if not force_rebuild:
                    existing = col.get(ids=[chunk_id], include=[])
                    if existing and existing.get("ids"):
                        skipped += 1
                        continue

                col.upsert(ids=[chunk_id], documents=[chunk], metadatas=[meta])
                added += 1

    return {"ok": True, "pdfs": len(pdfs), "added": added, "skipped": skipped}


def query(
    query_text: str,
    *,
    doc_type: Optional[str] = None,
    k: int = 5,
) -> List[RagChunk]:
    col = get_collection()
    where = {"doc_type": doc_type} if doc_type else None
    res = col.query(query_texts=[query_text], n_results=k, where=where, include=["documents", "metadatas", "distances"])

    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]

    chunks: List[RagChunk] = []
    for text, meta, dist in zip(docs, metas, dists):
        if not text:
            continue
        chunks.append(RagChunk(text=text, metadata=dict(meta or {}), distance=float(dist) if dist is not None else None))
    return chunks

