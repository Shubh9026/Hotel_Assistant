from __future__ import annotations

import contextvars
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional


_trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")
_user_message_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_message", default="")


_logger = logging.getLogger("service_trace")
# Ensure logs show up even if the app hasn't configured logging (default is WARNING).
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel(logging.INFO)
    _logger.addHandler(_handler)
    _logger.propagate = False


def get_trace_id() -> str:
    return _trace_id_var.get()


def get_user_message() -> str:
    return _user_message_var.get()


@contextmanager
def trace_context(*, trace_id: str, user_message: str = "") -> Iterator[None]:
    token_trace = _trace_id_var.set(trace_id or "-")
    token_msg = _user_message_var.set(user_message or "")
    try:
        yield
    finally:
        _trace_id_var.reset(token_trace)
        _user_message_var.reset(token_msg)


def log_service_call(service: str, action: str = "call", **payload: Any) -> None:
    """
    Log a compact JSON line describing a service invocation.
    `ensure_ascii=True` avoids Windows console encoding issues.
    """
    record: Dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "trace_id": get_trace_id(),
        "service": service,
        "action": action,
    }
    for k, v in payload.items():
        if v is None:
            continue
        record[k] = v

    _logger.info(json.dumps(record, ensure_ascii=True))
