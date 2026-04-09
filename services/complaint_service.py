from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from utils.json_storage import load_json, save_json
from utils.service_trace import log_service_call
from utils.mongo import get_db, mongo_enabled


COMPLAINTS_PATH = "data/write/complaints.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _complaints_collection():
    if not mongo_enabled():
        return None
    db = get_db()
    if db is None:
        return None
    return db["complaints"]


def _normalize_ticket(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    # Avoid leaking ObjectId types or confusing callers; keep `id` as the public key.
    if "id" not in doc and "_id" in doc:
        doc["id"] = doc.get("_id")
    if "_id" in doc:
        doc = dict(doc)
        doc.pop("_id", None)
    return doc


def _load_complaints() -> List[Dict[str, Any]]:
    data = load_json(COMPLAINTS_PATH)
    if isinstance(data, list):
        # Ensure list entries are dict-like.
        return [x for x in data if isinstance(x, dict)]
    return []


def _save_complaints(complaints: List[Dict[str, Any]]) -> None:
    save_json(COMPLAINTS_PATH, complaints)


def create_complaint_ticket(
    *,
    description: str,
    category: str,
    severity: str,
    location: str,
    room_number: Optional[int] = None,
    contact: Optional[str] = None,
) -> Dict[str, Any]:
    log_service_call(
        "complaint_service.create_complaint_ticket",
        category=category,
        severity=severity,
        location=location,
        room_number=room_number,
    )
    description = (description or "").strip()
    category = (category or "").strip().lower()
    severity = (severity or "").strip().lower()
    location = (location or "").strip()
    contact = (contact or "").strip() if contact else None

    if not description:
        raise ValueError("description is required")
    if not category:
        raise ValueError("category is required")
    if not severity:
        raise ValueError("severity is required")
    if not location:
        raise ValueError("location is required")

    if room_number is not None and room_number <= 0:
        room_number = None

    ticket_id = f"CMP-{uuid4().hex[:10].upper()}"
    ticket: Dict[str, Any] = {
        "id": ticket_id,
        "ts_created": _utc_now_iso(),
        "room_number": room_number,
        "location": location,
        "category": category,
        "severity": severity,
        "description": description,
        "contact": contact,
        "status": "open",
        "updates": [],
    }

    coll = _complaints_collection()
    if coll is not None:
        # Use the ticket id as the Mongo primary key for fast lookups.
        doc = dict(ticket)
        doc["_id"] = ticket_id
        coll.insert_one(doc)
        return ticket

    complaints = _load_complaints()
    complaints.append(ticket)
    _save_complaints(complaints)

    return ticket


def find_ticket(ticket_id: str) -> Optional[Dict[str, Any]]:
    if not ticket_id:
        return None
    ticket_id = ticket_id.strip()

    coll = _complaints_collection()
    if coll is not None:
        return _normalize_ticket(coll.find_one({"_id": ticket_id}))

    for t in _load_complaints():
        if t.get("id") == ticket_id:
            return t
    return None


def add_ticket_update(
    *,
    ticket_id: str,
    note: str,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    log_service_call(
        "complaint_service.add_ticket_update",
        ticket_id=ticket_id,
        status=status,
    )
    ticket_id = (ticket_id or "").strip()
    note = (note or "").strip()
    status = (status or "").strip().lower() if status else None

    if not ticket_id:
        raise ValueError("ticket_id is required")
    if not note:
        raise ValueError("note is required")

    coll = _complaints_collection()
    if coll is not None:
        update_doc: Dict[str, Any] = {
            "$push": {"updates": {"ts": _utc_now_iso(), "note": note}},
            "$set": {"ts_updated": _utc_now_iso()},
        }
        if status:
            update_doc["$set"]["status"] = status

        result = coll.update_one({"_id": ticket_id}, update_doc)
        if result.matched_count == 0:
            raise ValueError("ticket not found")
        return _normalize_ticket(coll.find_one({"_id": ticket_id})) or {}

    complaints = _load_complaints()
    for t in complaints:
        if t.get("id") != ticket_id:
            continue

        updates = t.get("updates")
        if not isinstance(updates, list):
            updates = []
            t["updates"] = updates

        updates.append({"ts": _utc_now_iso(), "note": note})
        t["ts_updated"] = _utc_now_iso()
        if status:
            t["status"] = status
        _save_complaints(complaints)
        return t

    raise ValueError("ticket not found")


def get_ticket_status(ticket_id: str) -> str:
    log_service_call("complaint_service.get_ticket_status", ticket_id=ticket_id)
    ticket = find_ticket(ticket_id)
    if not ticket:
        return "Sorry, I could not find that complaint ticket ID."

    room = ticket.get("room_number")
    room_str = f"room {room}" if isinstance(room, int) else "your location"
    return (
        f"Ticket {ticket.get('id')} is currently '{ticket.get('status')}'. "
        f"Category: {ticket.get('category')}, Severity: {ticket.get('severity')}, Location: {room_str}."
    )
