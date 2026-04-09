from datetime import datetime, timezone
import re
from uuid import uuid4

from utils.json_storage import append_json_list, load_json
from utils.service_trace import log_service_call
from utils.mongo import get_db, mongo_enabled


MENU_PATH = "data/read/room_service_menu.json"
ORDERS_PATH = "data/write/room_service_ordered.json"


def _normalize_item(item: str) -> str:
    # Keep the order tool robust to extra qualifiers like:
    # "coffee (vegan and peanut-free)", "tea, no sugar", etc.
    item = (item or "").lower().strip()
    item = re.split(r"[,(]", item, maxsplit=1)[0].strip()
    item = re.sub(r"\s+", " ", item)
    return item


def order_room_service(item: str, room_number: int):

    log_service_call("room_service.order_room_service", item=item, room_number=room_number)
    menu = load_json(MENU_PATH)

    item_raw = item or ""
    item_normalized = _normalize_item(item_raw)

    for category_name, category_items in (menu or {}).items():
        if item_normalized in (category_items or []):
            record = {
                "id": str(uuid4()),
                "ts": datetime.now(timezone.utc).isoformat(),
                "room_number": room_number,
                "item_raw": item_raw,
                "item": item_normalized,
                "category": category_name,
                "status": "ordered",
            }

            if mongo_enabled():
                db = get_db()
                if db is not None:
                    doc = dict(record)
                    doc["_id"] = record["id"]
                    db["room_service_orders"].insert_one(doc)
                else:
                    append_json_list(ORDERS_PATH, record)
            else:
                append_json_list(ORDERS_PATH, record)

            return f"{item_normalized.capitalize()} will be delivered to room {room_number} in about 25 minutes."

    return "Sorry, that item is not available in the room service menu."

    
