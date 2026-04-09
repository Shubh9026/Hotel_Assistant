# Hotel Guest Concierge (FastAPI + Ollama + MongoDB + RAG)

A lightweight **hotel concierge assistant** with chat-based room service, complaint tracking, hotel info Q&A, and local recommendations. Supports **Ollama (local LLM)**, **MongoDB / JSON storage**, and optional **RAG over PDFs**.

---

## Features

- FastAPI backend (`POST /chat`)
- Streamlit chat UI
- Local LLM via **Ollama**
- Room service ordering
- Complaint logging & tracking
- Hotel information Q&A
- Local recommendations
- MongoDB (optional) + JSON fallback
- Optional RAG (PDF → embeddings → ChromaDB)

---

## Repo Structure

```
main.py                  # FastAPI API (/chat)
streamlit_app.py         # Streamlit UI
agent/                   # Orchestrator + tools
services/                # Business logic
utils/                   # env, mongo, logging
data/read/               # hotel info, menu, recommendations
data/write/              # JSON fallback storage
data/docs/               # PDFs for RAG
data/chroma/             # vector DB
scripts/build_rag_index.py
```

---

## Requirements

- Python 3.11+
- Ollama running locally
- MongoDB (optional)

---

## Setup

### 1. Install

```bash
python -m venv .venv
source .venv/bin/activate  # windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. `.env`

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# optional
MONGO_URI=mongodb://localhost:27017
MONGO_DB=hotel_concierge

SERPER_API_KEY=YOUR_KEY
SERPER_GL=in
SERPER_HL=en
```

---

## Run Backend

```bash
uvicorn main:app --reload --port 8000
```

Swagger  
http://127.0.0.1:8000/docs

---

## Run UI

```bash
streamlit run streamlit_app.py
```

---

## Ollama Setup

Install + pull model

```bash
ollama pull llama3.1:8b
```

Verify running

```
http://localhost:11434
```

---

## API

### POST `/chat`

Request

```json
{
  "message": "Send coffee to room 204"
}
```

Response

```json
{
  "response": "Coffee will be delivered to room 204",
  "trace_id": "ABC123"
}
```

---

## Tools Supported

### Hotel Info
- breakfast time  
- checkout policy  
- wifi  
- amenities  

### Room Service
```
Send coffee to room 204
```

### Complaint Logging
```
AC not working in room 204
```

### Local Recommendations
```
Recommend restaurants nearby
```

---

## Storage Modes

### MongoDB (preferred)
Collections:
- complaints
- room_service_orders
- guest_profiles

### JSON fallback

```
data/write/complaints.json
data/write/room_service_ordered.json
data/write/guest_preference.json
```

---

## RAG Setup (Optional)

Add PDFs

```
data/docs/
```

Build index

```bash
python scripts/build_rag_index.py
```

Vector DB stored in

```
data/chroma/
```

---

## Example Prompts

- What time is breakfast?
- Send coffee to room 204
- AC not working in room 204
- Recommend restaurants nearby
- What is WiFi password?

---

## Tech Stack

FastAPI • Streamlit • Ollama • LangChain • MongoDB • ChromaDB • RAG
