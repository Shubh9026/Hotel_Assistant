from utils.env import load_env
from agent.orchestrator import handle_message
from services.guest_preference_service import update_guest_preferences


load_env()


def run_concierge_agent(user_input: str):
    # Track preference signals from the user's message (diet/allergies/likes, etc).
    # This is best-effort and will not block the main agent flow if parsing fails.
    try:
        update_guest_preferences(user_input)
    except Exception:
        pass

    return handle_message(user_input)
