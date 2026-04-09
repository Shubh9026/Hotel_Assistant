from fastapi import FastAPI
from pydantic import BaseModel
from uuid import uuid4

from agent.concierge import run_concierge_agent
from utils.service_trace import trace_context
from utils.env import load_env

load_env()

app = FastAPI()


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
def chat(request: ChatRequest):

    trace_id = uuid4().hex[:10].upper()
    with trace_context(trace_id=trace_id, user_message=request.message):
        response = run_concierge_agent(request.message)

    # Include trace_id for debugging (clients can ignore it).
    return {"response": response, "trace_id": trace_id}
