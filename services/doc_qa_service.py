from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from services.rag_store import RagChunk, query, rag_enabled
from utils.service_trace import log_service_call


_QA_SYSTEM_PROMPT = """You answer questions using ONLY the provided context.

Rules:
- Do not invent facts not present in the context.
- If the answer is not in the context, say you couldn't find it in the provided document.
- Be concise and helpful.
"""


def _llm() -> ChatOllama:
    return ChatOllama(
        base_url=os.getenv("OLLAMA_BASE_URL"),
        model=os.getenv("OLLAMA_MODEL"),
        temperature=0.2,
    )


def _format_context(chunks: List[RagChunk]) -> str:
    parts: List[str] = []
    for c in chunks:
        src = c.metadata.get("source", "document")
        page = c.metadata.get("page")
        ref = f"{src} p.{page}" if page else str(src)
        parts.append(f"[{ref}]\n{c.text}")
    return "\n\n---\n\n".join(parts)


def answer_from_docs(
    *,
    question: str,
    doc_type: str,
    k: int = 5,
) -> Optional[str]:
    """
    Return an answer grounded in PDFs indexed in Chroma.
    Returns None if RAG is not available.
    """
    if not rag_enabled():
        return None

    log_service_call("doc_qa_service.answer_from_docs", doc_type=doc_type, k=k)

    chunks = query(question, doc_type=doc_type, k=k)
    if not chunks:
        return "I couldn't find that information in the provided document."

    context = _format_context(chunks)
    prompt = f"""Context:
{context}

Question:
{question}
"""
    resp = _llm().invoke([SystemMessage(content=_QA_SYSTEM_PROMPT), HumanMessage(content=prompt)])
    text = (getattr(resp, "content", "") or "").strip()
    return text or "I couldn't find that information in the provided document."

