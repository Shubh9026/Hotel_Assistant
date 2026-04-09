from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx

from utils.service_trace import log_service_call
from utils.env import load_env


SERPER_ENDPOINT = os.getenv("SERPER_ENDPOINT", "https://google.serper.dev/search")


def _api_key() -> str:
    # Ensure env is loaded even when this module is imported outside `main.py`.
    load_env()
    return (os.getenv("SERPER_API_KEY") or "").strip()


def serper_enabled() -> bool:
    return bool(_api_key())


def _format_results(items: List[Dict[str, Any]], limit: int = 5) -> str:
    if not items:
        return "Sorry, I couldn't find recommendations right now."

    lines: List[str] = ["Here are some recommendations:\n"]
    for idx, item in enumerate(items[:limit], start=1):
        title = item.get("title") or item.get("name") or "Result"
        snippet = item.get("snippet") or item.get("description") or ""
        link = item.get("link") or item.get("website") or ""

        line = f"{idx}. {title}"
        if snippet:
            line += f" — {snippet}"
        if link:
            line += f"\n   {link}"
        lines.append(line)
    return "\n".join(lines).strip()


def search_recommendations(*, query: str, gl: str = "in", hl: str = "en", num: int = 5) -> str:
    """
    Run a Serper search query and return a formatted shortlist.
    Uses `SERPER_API_KEY` from the environment.
    """
    key = _api_key()
    if not key:
        raise RuntimeError("SERPER_API_KEY is not set")

    log_service_call("serper_service.search_recommendations", gl=gl, hl=hl)

    payload: Dict[str, Any] = {"q": query, "gl": gl, "hl": hl, "num": num, "autocorrect": True}
    headers = {"X-API-KEY": key, "Content-Type": "application/json"}

    with httpx.Client(timeout=20) as client:
        resp = client.post(SERPER_ENDPOINT, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # Prefer "places" if present (more location-like). Fall back to "organic".
    places = data.get("places")
    if isinstance(places, list) and places:
        return _format_results(places, limit=num)

    organic = data.get("organic")
    if isinstance(organic, list) and organic:
        return _format_results(organic, limit=num)

    return "Sorry, I couldn't find recommendations right now."
