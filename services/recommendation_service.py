import os
import re

from utils.json_storage import load_json
from utils.service_trace import log_service_call

from services.serper_service import search_recommendations, serper_enabled


DATA_PATH = "data/read/local_recommendations.json"


# Hardcoded from `data/docs/Hotel Handbook Detailed.pdf` (Address section on page 1).
DEFAULT_HOTEL_LOCATION = "Vipul Khand, Gomti Nagar, Lucknow, Uttar Pradesh – 226010"


def _looks_like_simple_category(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    return any(k in t for k in ["restaurant", "food", "cafe", "tourist", "attraction", "place", "things to do"])


def _serper_query(user_query: str, location: str) -> str:
    """
    Turn a user query into a Serper query string.
    If the user query looks like a broad category, expand it.
    Otherwise treat it as a free-form query and anchor it to a location.
    """
    q = (user_query or "").strip()
    loc = (location or "").strip()

    q_lower = q.lower()
    if _looks_like_simple_category(q_lower):
        if "restaurant" in q_lower or "food" in q_lower:
            return f"best restaurants near {loc}" if loc else "best restaurants nearby"
        if "cafe" in q_lower:
            return f"best cafes near {loc}" if loc else "best cafes nearby"
        if "tourist" in q_lower or "attraction" in q_lower or "place" in q_lower or "things to do" in q_lower:
            return f"top tourist attractions near {loc}" if loc else "top tourist attractions nearby"

    # Free-form query (events, concerts, specific things)
    if loc and " near " not in q_lower and " in " not in q_lower:
        # If user already said "nearby", anchor it to the location.
        if " nearby" in q_lower:
            return re.sub(r"\bnearby\b", f"near {loc}", q, flags=re.IGNORECASE).strip()
        return f"{q} near {loc}"
    return q or (f"things to do near {loc}" if loc else "things to do nearby")


def get_local_recommendations(query: str, location: str = ""):

    query = (query or "").strip()
    location = (location or "").strip()

    log_service_call(
        "recommendation_service.get_local_recommendations",
        query=query[:120],
        has_location=bool(location),
        provider="serper" if serper_enabled() else "json",
    )

    if serper_enabled():
        # Serper settings are optional; defaults match your current target locale.
        gl = (os.getenv("SERPER_GL") or "in").strip() or "in"
        hl = (os.getenv("SERPER_HL") or "en").strip() or "en"
        loc_text = location or DEFAULT_HOTEL_LOCATION
        q = _serper_query(query, loc_text)

        try:
            return search_recommendations(query=q, gl=gl, hl=hl, num=5)
        except Exception:
            # Fall back to local JSON if Serper fails (quota/network/etc).
            pass

    # JSON fallback only supports broad categories, not free-form web queries.
    category = query.lower()
    data = load_json(DATA_PATH)

    if "restaurant" in category or "food" in category:
        places = data.get("restaurants", [])

    elif "cafe" in category:
        places = data.get("cafes", [])

    elif "tourist" in category or "place" in category:
        places = data.get("tourist_places", [])

    else:
        return (
            "Web recommendations are not available right now. "
            "I can recommend restaurants, cafes, or tourist attractions nearby."
        )

    if not places:
        return "Sorry, I couldn't find recommendations right now."

    response = "Here are some recommendations:\n\n"

    for i, place in enumerate(places, start=1):
        if "rating" in place:
            response += f"{i}. {place['name']} - {place['rating']} stars\n"
        else:
            response += f"{i}. {place['name']}\n"

    return response
