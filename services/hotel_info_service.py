from utils.json_storage import load_json
import json


DATA_PATH = "data/read/hotel_info.json"


from utils.json_storage import load_json
import json
from typing import Dict, Any
import re


DATA_PATH = "data/read/hotel_info.json"


def get_hotel_info(question: str) -> str:
    """
    Answer questions about hotel information using semantic understanding
    """
    from utils.service_trace import log_service_call
    from services.doc_qa_service import answer_from_docs

    log_service_call("hotel_info_service.get_hotel_info", question=question)

    # Prefer RAG over PDFs when available; fall back to JSON heuristics otherwise.
    try:
        rag_answer = answer_from_docs(question=question, doc_type="hotel_info")
        if rag_answer:
            return rag_answer
    except Exception:
        pass

    data = load_json(DATA_PATH)
    question = question.lower().strip()

    # Direct keyword matching for common queries
    if any(word in question for word in ["name", "called", "hotel name"]):
        return f"The name of our hotel is {data.get('name', 'Taj Palace Delhi')}."

    if any(word in question for word in ["location", "address", "where", "city"]):
        location = data.get('location', {})
        return f"Our hotel is located at {location.get('address', '')}, {location.get('city', '')}, {location.get('country', '')}."

    if any(word in question for word in ["breakfast", "dining hours"]):
        return f"Breakfast: {data.get('breakfast', 'Not available')}"

    if any(word in question for word in ["checkout", "check-out", "check out time"]):
        return f"Checkout time: {data.get('checkout', 'Not available')}"

    if any(word in question for word in ["wifi", "internet", "wi-fi"]):
        return f"WiFi: {data.get('wifi', 'Not available')}"

    if any(word in question for word in ["gym", "fitness", "exercise"]):
        return f"Gym: {data.get('gym', 'Not available')}"

    if any(word in question for word in ["pool", "swimming", "swim"]):
        return f"Pool: {data.get('pool', 'Not available')}"

    if any(word in question for word in ["contact", "phone", "email", "website"]):
        contact = data.get('contact', {})
        response = "Contact Information:\n"
        response += f"Phone: {contact.get('phone', 'Not available')}\n"
        response += f"Email: {contact.get('email', 'Not available')}\n"
        response += f"Website: {contact.get('website', 'Not available')}"
        return response

    # For general questions about the hotel
    if any(word in question for word in ["about", "tell me", "describe", "information", "overview"]):
        return get_general_hotel_info(data)

    # For amenities
    if any(word in question for word in ["amenities", "facilities", "services", "what do you offer"]):
        return get_amenities_info(data)

    # For policies
    if any(word in question for word in ["policies", "rules", "policy", "cancellation"]):
        return get_policies_info(data)

    # For rooms
    if any(word in question for word in ["rooms", "room types", "accommodation"]):
        return get_rooms_info(data)

    # Try semantic matching for other queries
    return find_relevant_info(question, data)


def get_general_hotel_info(data):
    """Return comprehensive hotel information"""
    name = data.get('name', 'Taj Palace Delhi')
    description = data.get('description', '')
    location = data.get('location', {})
    address = location.get('address', '')
    city = location.get('city', '')

    response = f"{name} - {description}\n\n"
    response += f"Location: {address}, {city}\n\n"

    # Add key amenities
    amenities = data.get('amenities', {})
    if 'dining' in amenities:
        response += "Dining Options:\n"
        dining = amenities['dining']
        for key, value in dining.items():
            response += f"- {value}\n"

    if 'fitness' in amenities:
        response += "\nFitness & Wellness:\n"
        fitness = amenities['fitness']
        for key, value in fitness.items():
            response += f"- {value}\n"

    response += f"\nBreakfast: {data.get('breakfast', '')}\n"
    response += f"Checkout: {data.get('checkout', '')}\n"
    response += f"WiFi: {data.get('wifi', '')}"

    return response


def get_amenities_info(data):
    """Return information about hotel amenities"""
    amenities = data.get('amenities', {})
    response = "Our hotel offers the following amenities:\n\n"

    for category, items in amenities.items():
        response += f"{category.capitalize()}:\n"
        if isinstance(items, dict):
            for key, value in items.items():
                response += f"- {value}\n"
        response += "\n"

    return response


def get_policies_info(data):
    """Return information about hotel policies"""
    policies = data.get('policies', {})
    response = "Hotel Policies:\n\n"

    for policy, value in policies.items():
        response += f"- {policy.replace('_', ' ').capitalize()}: {value}\n"

    return response


def find_relevant_info(question: str, data: Dict[str, Any]) -> str:
    """
    Use simple semantic matching to find relevant information
    """
    question_words = set(re.findall(r'\b\w+\b', question.lower()))

    best_match = None
    best_score = 0

    # Flatten the data structure and search for matches
    def search_dict(d, path=""):
        nonlocal best_match, best_score
        for key, value in d.items():
            if isinstance(value, dict):
                search_dict(value, f"{path}.{key}" if path else key)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, str):
                        item_words = set(re.findall(r'\b\w+\b', item.lower()))
                        score = len(question_words.intersection(item_words))
                        if score > best_score:
                            best_score = score
                            best_match = item
                    elif isinstance(item, dict):
                        search_dict(item, f"{path}.{key}[{i}]")
            elif isinstance(value, str):
                value_words = set(re.findall(r'\b\w+\b', value.lower()))
                score = len(question_words.intersection(value_words))
                if score > best_score:
                    best_score = score
                    best_match = f"{key.replace('_', ' ').title()}: {value}"

    search_dict(data)

    if best_match and best_score > 0:
        return best_match

    return "I'm sorry, I couldn't find specific information about that. Please ask about our hotel name, location, amenities, policies, or specific services."


def get_rooms_info(data):
    """Return information about rooms"""
    rooms = data.get('rooms', {})
    response = "🏠 Room Information:\n\n"

    response += f"Total Rooms: {rooms.get('total_rooms', 'N/A')}\n\n"
    response += "Room Types:\n"
    for room_type in rooms.get('room_types', []):
        response += f"• {room_type}\n"

    response += "\nStandard Features:\n"
    for feature in rooms.get('features', []):
        response += f"• {feature}\n"

    return response


    
