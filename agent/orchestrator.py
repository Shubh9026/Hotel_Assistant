from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from agent.prompts import ORCHESTRATOR_MERGE_SYSTEM_PROMPT, ORCHESTRATOR_ROUTER_SYSTEM_PROMPT
from agent.tools import (
    complaint_status,
    hotel_information,
    local_recommendations,
    log_complaint,
    room_service,
    room_service_menu_information,
    update_complaint,
)


ToolFn = Any


@dataclass(frozen=True)
class ToolCall:
    tool: str
    args: Dict[str, Any]


def _build_llm() -> ChatOllama:
    return ChatOllama(
        base_url=os.getenv("OLLAMA_BASE_URL"),
        model=os.getenv("OLLAMA_MODEL"),
        temperature=0.2,
    )


TOOL_REGISTRY: Dict[str, Tuple[ToolFn, str]] = {
    "hotel_information": (
        hotel_information,
        "Get accurate hotel details (breakfast, checkout, wifi, amenities, policies). Args: {question:str}",
    ),
    "local_recommendations": (
        local_recommendations,
        "Get web-powered recommendations (places/events). Args: {query:str, location?:str}",
    ),
    "room_service_menu_information": (
        room_service_menu_information,
        "Answer questions about the room service menu (items, hours, allergens, pricing if present). Args: {question:str}",
    ),
    "room_service": (
        room_service,
        "Order room service items. Args: {item:str, room_number:int}",
    ),
    "log_complaint": (
        log_complaint,
        "Create a complaint ticket. Args: {description:str, category:str, severity:str, location:str, room_number?:int, contact?:str}",
    ),
    "complaint_status": (
        complaint_status,
        "Check complaint ticket status. Args: {ticket_id:str}",
    ),
    "update_complaint": (
        update_complaint,
        "Add note/update to complaint. Args: {ticket_id:str, note:str, status?:str}",
    ),
}


def _tools_markdown() -> str:
    lines = []
    for name, (_, desc) in TOOL_REGISTRY.items():
        lines.append(f"- {name}: {desc}")
    return "\n".join(lines)


def _extract_json_object(text: str) -> Optional[str]:
    """
    Best-effort extraction of a JSON object from LLM output.
    """
    text = (text or "").strip()
    if not text:
        return None
    if text.startswith("{") and text.endswith("}"):
        return text
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    return m.group(0) if m else None


def _parse_router_output(raw: str) -> Dict[str, Any]:
    obj = _extract_json_object(raw)
    if not obj:
        raise ValueError("router did not return JSON")
    return json.loads(obj)


def _validate_calls(calls: List[Dict[str, Any]]) -> List[ToolCall]:
    validated: List[ToolCall] = []
    for c in calls:
        if not isinstance(c, dict):
            continue
        tool = c.get("tool")
        args = c.get("args")
        if not isinstance(tool, str) or tool not in TOOL_REGISTRY:
            continue
        if not isinstance(args, dict):
            args = {}
        validated.append(ToolCall(tool=tool, args=args))
    return validated[:6]


def _execute_tool_call(call: ToolCall) -> str:
    fn, _ = TOOL_REGISTRY[call.tool]
    try:
        # LangChain tools (from @tool) are usually BaseTool instances with .invoke().
        if hasattr(fn, "invoke"):
            result = fn.invoke(call.args)
        else:
            result = fn(**call.args)
        return str(result)
    except TypeError as e:
        return f"Tool error calling {call.tool}: {e}"
    except Exception as e:
        return f"Tool error calling {call.tool}: {e}"


def handle_message(user_message: str) -> str:
    """
    Orchestrate a user request:
    - LLM decides direct vs tools
    - Execute tool calls (if any)
    - LLM merges tool outputs into final answer
    """
    llm = _build_llm()

    router_user = f"""User message:
{user_message}

Available tools:
{_tools_markdown()}
"""
    router_resp = llm.invoke(
        [
            SystemMessage(content=ORCHESTRATOR_ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=router_user),
        ]
    )
    router_text = getattr(router_resp, "content", "") or ""

    try:
        plan = _parse_router_output(router_text)
    except Exception:
        # Fallback: safe direct answer.
        return (
            "Sorry — I had trouble deciding which hotel tools to use for that request. "
            "Could you rephrase it or ask one thing at a time?"
        )

    mode = plan.get("mode")
    if mode == "direct":
        final = plan.get("final_answer")
        if isinstance(final, str) and final.strip():
            return final.strip()
        # If the router chose direct but didn't provide an answer, ask LLM once.
        direct = llm.invoke(
            [
                SystemMessage(content=ORCHESTRATOR_MERGE_SYSTEM_PROMPT),
                HumanMessage(content=user_message),
            ]
        )
        return (getattr(direct, "content", "") or "").strip() or "Sorry, I couldn't answer that."

    if mode != "tools":
        return "Sorry, I couldn't understand your request. Can you rephrase?"

    calls_raw = plan.get("calls", [])
    calls = _validate_calls(calls_raw if isinstance(calls_raw, list) else [])
    if not calls:
        return (
            "I couldn't find any actionable tool calls for that request. "
            "Could you be more specific (e.g., room number, category, or ticket id)?"
        )

    observations: List[Dict[str, Any]] = []
    for c in calls:
        observations.append(
            {
                "tool": c.tool,
                "args": c.args,
                "output": _execute_tool_call(c),
            }
        )

    merge_user = json.dumps(
        {"user_message": user_message, "tool_observations": observations},
        ensure_ascii=False,
        indent=2,
    )
    merged = llm.invoke(
        [
            SystemMessage(content=ORCHESTRATOR_MERGE_SYSTEM_PROMPT),
            HumanMessage(content=merge_user),
        ]
    )
    return (getattr(merged, "content", "") or "").strip() or "Sorry, I couldn't generate a response."
