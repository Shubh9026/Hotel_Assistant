from __future__ import annotations

from typing import Optional

from services.doc_qa_service import answer_from_docs
from utils.service_trace import log_service_call


def get_room_service_menu_info(question: str) -> str:
    """
    Answer questions about the room service menu using RAG over PDFs (if available).
    Falls back to a helpful message if docs are not configured yet.
    """
    log_service_call("menu_info_service.get_room_service_menu_info", question=question)
    answer = answer_from_docs(question=question, doc_type="room_service")
    if answer:
        return answer
    return (
        "Room service menu documents are not configured yet. "
        "Please add a room service menu PDF under data/docs/ and build the index."
    )

