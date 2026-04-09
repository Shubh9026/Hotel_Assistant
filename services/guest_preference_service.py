import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from utils.json_storage import load_json, save_json
from utils.service_trace import log_service_call
from utils.mongo import get_db, mongo_enabled


PREFERENCES_PATH = "data/write/guest_preference.json"


def _uniq_extend(target: List[str], items: List[str]) -> List[str]:
    seen = {x.lower() for x in target if isinstance(x, str)}
    for item in items:
        if not item:
            continue
        key = item.lower()
        if key not in seen:
            target.append(item)
            seen.add(key)
    return target


def _extract_room_number(text: str) -> Optional[int]:
    m = re.search(r"\broom\s*#?\s*(\d{1,5})\b", text, flags=re.IGNORECASE)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def extract_preferences_from_text(text: str) -> Dict[str, Any]:
    """
    Lightweight heuristics for preference tracking from user chat messages.
    This avoids extra LLM calls and works even if the model is offline.
    """
    if not text:
        return {}

    lowered = text.lower()
    extracted: Dict[str, Any] = {}

    room_number = _extract_room_number(text)
    if room_number is not None:
        extracted["room_number"] = room_number

    diets = []
    for diet in ["vegetarian", "vegan", "halal", "kosher", "gluten-free", "gluten free"]:
        if diet in lowered:
            diets.append("gluten-free" if diet == "gluten free" else diet)
    if diets:
        extracted["diet"] = diets

    allergies = []
    # Examples: "I'm allergic to peanuts", "no nuts please", "avoid shellfish"
    allergy_patterns = [
        r"\ballergic to ([\w\s-]+)",
        r"\bavoid ([\w\s-]+)",
        r"\bno ([\w\s-]+) please\b",
        r"\bno ([\w\s-]+)\b",
    ]
    for pat in allergy_patterns:
        for m in re.finditer(pat, lowered):
            candidate = m.group(1).strip()
            # Keep it short to avoid capturing whole sentences.
            candidate = candidate.split(" and ")[0].split(",")[0].strip()
            if 1 <= len(candidate) <= 32:
                allergies.append(candidate)
    if allergies:
        extracted["allergies"] = allergies

    likes = []
    dislikes = []
    like_patterns = [r"\bi (?:prefer|like|love) ([\w\s-]+)"]
    dislike_patterns = [r"\bi (?:don't like|do not like|hate) ([\w\s-]+)"]
    for pat in like_patterns:
        for m in re.finditer(pat, lowered):
            candidate = m.group(1).strip().split(" over ")[0].split(",")[0].strip()
            if 1 <= len(candidate) <= 32:
                likes.append(candidate)
    for pat in dislike_patterns:
        for m in re.finditer(pat, lowered):
            candidate = m.group(1).strip().split(",")[0].strip()
            if 1 <= len(candidate) <= 32:
                dislikes.append(candidate)
    if likes:
        extracted["likes"] = likes
    if dislikes:
        extracted["dislikes"] = dislikes

    return extracted


def update_guest_preferences(message: str) -> Optional[Dict[str, Any]]:
    """
    Update the preference store if we can extract any preference signals.

    Returns the extracted payload if an update was written, else None.
    """
    extracted = extract_preferences_from_text(message)
    if not extracted:
        return None

    log_service_call(
        "guest_preference_service.update_guest_preferences",
        room_number=extracted.get("room_number"),
        has_diet=bool(extracted.get("diet")),
        has_allergies=bool(extracted.get("allergies")),
        has_likes=bool(extracted.get("likes")),
        has_dislikes=bool(extracted.get("dislikes")),
    )

    store = load_json(PREFERENCES_PATH)
    if not isinstance(store, dict):
        store = {}

    profiles = store.get("profiles")
    if not isinstance(profiles, dict):
        profiles = {}
        store["profiles"] = profiles

    room_number = extracted.get("room_number")
    guest_key = f"room-{room_number}" if isinstance(room_number, int) else "anonymous"

    if mongo_enabled():
        db = get_db()
        if db is not None:
            coll = db["guest_profiles"]
            profile = coll.find_one({"_id": guest_key})
            if not isinstance(profile, dict):
                profile = {
                    "_id": guest_key,
                    "room_number": room_number if isinstance(room_number, int) else None,
                    "diet": [],
                    "allergies": [],
                    "likes": [],
                    "dislikes": [],
                    "history": [],
                }

            profile["last_message_ts"] = datetime.now(timezone.utc).isoformat()

            if "diet" in extracted:
                diet_list = profile.get("diet")
                if not isinstance(diet_list, list):
                    diet_list = []
                _uniq_extend(diet_list, extracted.get("diet", []))
                profile["diet"] = diet_list
            if "allergies" in extracted:
                allergy_list = profile.get("allergies")
                if not isinstance(allergy_list, list):
                    allergy_list = []
                _uniq_extend(allergy_list, extracted.get("allergies", []))
                profile["allergies"] = allergy_list
            if "likes" in extracted:
                likes_list = profile.get("likes")
                if not isinstance(likes_list, list):
                    likes_list = []
                _uniq_extend(likes_list, extracted.get("likes", []))
                profile["likes"] = likes_list
            if "dislikes" in extracted:
                dislikes_list = profile.get("dislikes")
                if not isinstance(dislikes_list, list):
                    dislikes_list = []
                _uniq_extend(dislikes_list, extracted.get("dislikes", []))
                profile["dislikes"] = dislikes_list

            history = profile.get("history")
            if not isinstance(history, list):
                history = []
                profile["history"] = history
            history.append(
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "message": message,
                    "extracted": extracted,
                }
            )

            coll.replace_one({"_id": guest_key}, profile, upsert=True)
            return extracted

    profile = profiles.get(guest_key)
    if not isinstance(profile, dict):
        profile = {
            "room_number": room_number if isinstance(room_number, int) else None,
            "diet": [],
            "allergies": [],
            "likes": [],
            "dislikes": [],
            "history": [],
        }
        profiles[guest_key] = profile

    profile["last_message_ts"] = datetime.now(timezone.utc).isoformat()

    if "diet" in extracted:
        _uniq_extend(profile["diet"], extracted.get("diet", []))
    if "allergies" in extracted:
        _uniq_extend(profile["allergies"], extracted.get("allergies", []))
    if "likes" in extracted:
        _uniq_extend(profile["likes"], extracted.get("likes", []))
    if "dislikes" in extracted:
        _uniq_extend(profile["dislikes"], extracted.get("dislikes", []))

    history = profile.get("history")
    if not isinstance(history, list):
        history = []
        profile["history"] = history
    history.append(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "message": message,
            "extracted": extracted,
        }
    )

    save_json(PREFERENCES_PATH, store)
    return extracted
