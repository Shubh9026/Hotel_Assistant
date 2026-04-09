from __future__ import annotations

import os
from typing import Any, Optional


_client: Any = None
_db: Any = None
_indexes_ensured: bool = False


def mongo_enabled() -> bool:
    return bool(os.getenv("MONGO_URI"))


def get_db():
    """
    Return a cached pymongo database handle.

    This module is intentionally import-safe even when `pymongo` isn't installed:
    we only import pymongo when Mongo is actually enabled via env vars.
    """
    global _client, _db

    if _db is not None:
        return _db

    uri = os.getenv("MONGO_URI")
    if not uri:
        return None

    db_name = os.getenv("MONGO_DB", "hotel_concierge")

    try:
        from pymongo import MongoClient  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "MongoDB is enabled (MONGO_URI is set) but pymongo is not installed. "
            "Add `pymongo` to requirements and install dependencies."
        ) from e

    _client = MongoClient(uri)
    _db = _client[db_name]
    ensure_indexes()
    return _db


def ensure_indexes() -> None:
    """
    Best-effort index creation for collections we use.
    Safe to call multiple times.
    """
    global _indexes_ensured
    if _indexes_ensured:
        return

    db = get_db()
    if db is None:
        return

    try:
        # Complaint tickets
        db["complaints"].create_index("id", unique=True)
        db["complaints"].create_index("status")
        db["complaints"].create_index("room_number")

        # Room service orders
        db["room_service_orders"].create_index("id", unique=True)
        db["room_service_orders"].create_index("room_number")
        db["room_service_orders"].create_index("status")

        # Guest preference profiles: use Mongo _id as the guest_key
        db["guest_profiles"].create_index("room_number")
    finally:
        _indexes_ensured = True
