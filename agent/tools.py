from langchain.tools import tool

from services.hotel_info_service import get_hotel_info
from services.recommendation_service import get_local_recommendations
from services.menu_info_service import get_room_service_menu_info
from services.room_service import order_room_service
from services.complaint_service import add_ticket_update, create_complaint_ticket, get_ticket_status


@tool
def hotel_information(question: str) -> str:
    """Get accurate information about the hotel including name, location, amenities, policies, and services.
    Use this tool for ANY questions about the hotel itself - name, location, facilities, policies, dining, etc.
    Do NOT make up information - this tool provides real data from the hotel database."""
    return get_hotel_info(question)


@tool
def local_recommendations(query: str, location: str = "") -> str:
    """Get web-powered local recommendations (via Serper when configured).

    Use this for:
    - places: restaurants/cafes/attractions near a location
    - events: concerts/shows/activities near a location

    Args:
    - query: free-form text (e.g. 'restaurants', 'tourist attractions', 'Honey Singh concert')
    - location (optional): area/city text like 'Aliganj Lucknow', 'Connaught Place Delhi'.
    """
    return get_local_recommendations(query, location=location)


@tool
def room_service_menu_information(question: str) -> str:
    """Answer questions about the room service menu: items, categories, hours, allergens, pricing (if present).
    Use this tool when the guest is ASKING about the menu, not placing an order."""
    return get_room_service_menu_info(question)


@tool
def room_service(item: str, room_number: int) -> str:
    """Order room service items. Use this for food, drinks, or other items to be delivered to guest rooms.
    Requires item description and room number."""
    return order_room_service(item, room_number)


@tool
def log_complaint(
    description: str,
    category: str,
    severity: str,
    location: str,
    room_number: int = 0,
    contact: str = "",
) -> str:
    """Log a guest complaint and create a ticket.

    Use this tool whenever the guest is unhappy, reporting an issue, or asking to file a complaint.
    Required: description, category, severity, location.
    Optional: room_number, contact.

    Categories (examples): housekeeping, maintenance, noise, food, staff, billing, safety, other.
    Severity (examples): low, medium, high, critical.
    """
    ticket = create_complaint_ticket(
        description=description,
        category=category,
        severity=severity,
        location=location,
        room_number=room_number if room_number and room_number > 0 else None,
        contact=contact or None,
    )
    return (
        f"Thanks for reporting this. I have logged your complaint as ticket {ticket['id']} "
        f"with status '{ticket['status']}'. Our team will look into it."
    )


@tool
def complaint_status(ticket_id: str) -> str:
    """Check the current status of a previously logged complaint ticket by ticket ID."""
    return get_ticket_status(ticket_id)


@tool
def update_complaint(ticket_id: str, note: str, status: str = "") -> str:
    """Add an update note to a complaint ticket (and optionally set a new status).

    Status (optional): open, assigned, resolved, closed.
    """
    updated = add_ticket_update(ticket_id=ticket_id, note=note, status=status or None)
    return f"Updated ticket {updated.get('id')} with status '{updated.get('status')}'."


TOOLS = [
    hotel_information,
    local_recommendations,
    room_service_menu_information,
    room_service,
    log_complaint,
    complaint_status,
    update_complaint,
]
