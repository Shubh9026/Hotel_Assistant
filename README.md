# Hotel Guest Concierge (FastAPI + Ollama + MongoDB + RAG)

A prototype **hotel concierge assistant** with:

- **Backend API**: FastAPI (`POST /chat`)
- **UI**: Streamlit chat client
- **LLM**: Local **Ollama** via `langchain-ollama`
- **Tools / actions**: room service ordering, complaint logging & status, hotel info Q&A, local recommendations
- **Storage**:
  - **MongoDB** (optional; preferred for writes)
  - **JSON files** fallback under `data/write/`
- **RAG** (optional): PDF → chunks → embeddings → **ChromaDB** persistent index under `data/chroma/`

---

## Repo layout

- `main.py` — FastAPI app (single endpoint: `/chat`)
- `streamlit_app.py` — Streamlit UI that calls the backend API
- `agent/` — orchestrator, tools registry, prompts
- `services/` — business logic (hotel info, menu Q&A, room service, complaints, recommendations, RAG)
- `utils/` — env loading, Mongo helpers, JSON storage, tracing
- `data/read/` — curated JSON data (hotel info, local recommendations, room service menu)
- `data/write/` — write-store JSON fallback (complaints, guest profiles, orders)
- `data/docs/` — PDFs used for RAG (hotel handbook / policies / menu)
- `data/chroma/` — persisted ChromaDB index files
- `scripts/build_rag_index.py` — builds/updates the Chroma index from PDFs

---

## Prerequisites

- **Python**: 3.11+ (3.12 recommended)
- **Ollama** installed and running (for chat + RAG answering)
- **MongoDB** (optional; if enabled via `MONGO_URI`)

---

## Setup

### 1) Create a virtual environment & install dependencies

PowerShell (Windows):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure environment variables (`.env`)

This project loads `.env` from the repo root via `utils/env.py`.

Required for chat:

- `OLLAMA_BASE_URL` (default Ollama: `http://localhost:11434`)
- `OLLAMA_MODEL` (any model you have in Ollama)

Optional:

- `MONGO_URI` / `MONGO_DB` (enables MongoDB writes)
- `SERPER_API_KEY` / `SERPER_GL` / `SERPER_HL` (enables web recommendations via Serper)
- `RAG_DOCS_DIR` / `RAG_CHROMA_DIR` / `RAG_COLLECTION` / `RAG_EMBED_MODEL` (advanced RAG settings; defaults are fine)

Example `.env` (do **not** paste real API keys into README):

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Mongo (optional)
MONGO_URI=mongodb://localhost:27017
MONGO_DB=hotel_concierge

# Serper (optional)
SERPER_API_KEY=YOUR_KEY_HERE
SERPER_GL=in
SERPER_HL=en
```

Security note: the current `.env` in this repo contains a `SERPER_API_KEY`. If this is a real key, rotate it and avoid committing secrets.

---

## Running the backend (FastAPI)

Start the API server:

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Interactive docs:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

---

## Running the UI (Streamlit)

With the backend running, start the UI:

```powershell
streamlit run streamlit_app.py
```

The UI calls the backend at `http://127.0.0.1:8000/chat` (configured in `streamlit_app.py`).

---

## Ollama setup

1) Install Ollama (platform-specific).
2) Ensure the server is running (default listens on `http://localhost:11434`).
3) Pull a model and set `OLLAMA_MODEL` accordingly, e.g.:

```bash
ollama pull llama3.1:8b
```

If you see errors like “model not found”, update `OLLAMA_MODEL` to a model you have locally.

---

## Database & storage

This project supports **two storage modes**:

### Mode A — MongoDB (preferred)

Mongo is enabled when `MONGO_URI` is set (see `utils/mongo.py:mongo_enabled()`).

Collections used:

- `complaints`
- `room_service_orders`
- `guest_profiles`

Indexes are created automatically on startup (best-effort) via `utils/mongo.py:ensure_indexes()`:

- `complaints`: `id` (unique), `status`, `room_number`
- `room_service_orders`: `id` (unique), `room_number`, `status`
- `guest_profiles`: `room_number` (Mongo `_id` is the guest key)

**MongoDB local setup (example)**

- Install MongoDB Community Edition (or use Docker)
- Ensure it’s listening on `localhost:27017`
- Set:
  - `MONGO_URI=mongodb://localhost:27017`
  - `MONGO_DB=hotel_concierge`

### Mode B — JSON files (fallback)

If `MONGO_URI` is **not** set, writes go to JSON files under `data/write/`:

- `data/write/complaints.json`
- `data/write/room_service_ordered.json`
- `data/write/guest_preference.json`

This is useful for demos where you don’t want to run MongoDB.
To force JSON mode, remove/comment `MONGO_URI` (and optionally `MONGO_DB`) from `.env`.

---

## RAG (PDF Q&A) setup

RAG is enabled when at least one PDF exists in `data/docs/` (see `services/rag_store.py:rag_enabled()`).

Defaults:

- PDFs: `data/docs/*.pdf`
- ChromaDB: `data/chroma/`
- Collection: `hotel_docs`
- Embedding model: `all-MiniLM-L6-v2` (SentenceTransformers)

### Build / update the index

```powershell
python scripts/build_rag_index.py
```

What it does:

- Reads all PDFs in `data/docs/`
- Splits pages into overlapping character chunks
- Stores embeddings + metadata in a persistent Chroma collection

Metadata stored per chunk:

- `source` (pdf filename)
- `page` (page number)
- `doc_type` (inferred: `room_service` if filename contains “menu”, else `hotel_info`)

Note: `services/menu_info_service.py` and parts of `services/hotel_info_service.py` prefer RAG answers when available.
The first run may download the embedding model (`RAG_EMBED_MODEL`) and can take a few minutes.

---

## Backend API (HTTP)

### `POST /chat`

Send a user message and receive the concierge response.

**Request**

- Content-Type: `application/json`
- Body:

```json
{
  "message": "Send coffee to room 204"
}
```

**Response**

```json
{
  "response": "Coffee will be delivered to room 204 in about 25 minutes.",
  "trace_id": "A1B2C3D4E5"
}
```

`trace_id` is included to correlate server logs (see “Tracing & logs”).

**Bash cURL**

```bash
curl -s http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"What time is breakfast?"}'
```

**PowerShell**

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat `
  -ContentType 'application/json' `
  -Body (@{ message = 'What time is breakfast?' } | ConvertTo-Json)
```

**Common errors**

- `422 Unprocessable Entity`: body missing `message` or wrong JSON shape
- `500 Internal Server Error`: downstream failures (Ollama not running, missing deps, etc.)

---

## “Tools” (internal action APIs)

The backend has a single HTTP endpoint. Internally, the agent can call these tools (see `agent/tools.py` and `agent/orchestrator.py`).

### 1) `hotel_information(question: str) -> str`

Used for hotel facts: breakfast, checkout, wifi, amenities, policies, etc.

Implementation:

- First tries RAG via `services/doc_qa_service.answer_from_docs(doc_type="hotel_info")`
- Falls back to `data/read/hotel_info.json` with keyword + simple semantic matching

Data source:

- `data/read/hotel_info.json`

### 2) `local_recommendations(query: str, location: str="") -> str`

Used for nearby restaurants/cafes/tourist places and events.

Implementation (`services/recommendation_service.py`):

- If `SERPER_API_KEY` is set, uses Serper web search
- Otherwise falls back to `data/read/local_recommendations.json` (category-based only)

Env:

- `SERPER_API_KEY` (enables Serper)
- `SERPER_GL`, `SERPER_HL` (locale; defaults to `in`/`en`)

### 3) `room_service_menu_information(question: str) -> str`

Answers questions about the room service menu using RAG (PDFs).

Implementation:

- Uses `services/doc_qa_service.answer_from_docs(doc_type="room_service")`
- If RAG not set up, returns a message asking to add PDFs and build the index

### 4) `room_service(item: str, room_number: int) -> str`

Places a room service order.

Implementation (`services/room_service.py`):

- Reads menu from `data/read/room_service_menu.json`
- Normalizes the requested item and matches it to available menu items
- Writes an order record to:
  - Mongo: `room_service_orders` (if enabled), else
  - JSON: `data/write/room_service_ordered.json`

### 5) `log_complaint(...) -> str`

Creates a complaint ticket and returns a confirmation message with ticket id.

Implementation (`services/complaint_service.py:create_complaint_ticket`):

- Writes to:
  - Mongo: `complaints` (with `_id = ticket_id`) if enabled, else
  - JSON: `data/write/complaints.json`

Ticket id format:

- `CMP-XXXXXXXXXX` (10 hex chars)

### 6) `complaint_status(ticket_id: str) -> str`

Fetches a complaint ticket and returns a human-readable status.

### 7) `update_complaint(ticket_id: str, note: str, status: str="") -> str`

Adds a note to an existing complaint ticket (and optionally updates its status).

Statuses are free-form strings but intended values are:

- `open`, `assigned`, `resolved`, `closed`

---

## Data schemas (what’s stored)

### `data/read/hotel_info.json`

Curated hotel details used for fallback Q&A:

- `name`, `description`
- `location` (address, city, country, pincode, coordinates, nearby_attractions)
- `contact` (phone, email, website)
- `policies` (check-in/out, cancellation, pets, smoking, etc.)
- `amenities` (dining, fitness, business, other)
- `rooms` (types, features)
- `services`, `accessibility`, `cultural_experiences`
- Convenience fields: `breakfast`, `checkout`, `wifi`, `gym`, `pool`

### `data/read/room_service_menu.json`

Room service menu categories → array of item strings, e.g.:

- `food`: `["pasta", "burger", ...]`
- `drinks`: `["coffee", "tea", ...]`
- `other`: `["extra towels", ...]`

### `data/write/room_service_ordered.json` (JSON fallback)

Top-level list of order records, example fields:

- `id` (uuid string)
- `ts` (UTC ISO)
- `room_number` (int)
- `item_raw` (optional; original text)
- `item` (normalized)
- `category` (`food`/`drinks`/`other`)
- `status` (default: `ordered`)

Mongo equivalent: `room_service_orders` with `_id = id`.

### `data/write/complaints.json` (JSON fallback)

Top-level list of complaint tickets:

- `id` (e.g. `CMP-41AB20D8C6`)
- `ts_created`, `ts_updated` (UTC ISO)
- `room_number` (int or null)
- `location` (string)
- `category` (string; normalized lowercase)
- `severity` (string; normalized lowercase)
- `description` (string)
- `contact` (string or null)
- `status` (string; default `open`)
- `updates`: list of `{ts, note}`

Mongo equivalent: `complaints` with `_id = id`.

### `data/write/guest_preference.json` (JSON fallback)

Top-level object with `profiles`:

- key: `room-<number>` if the message includes “room <n>”, otherwise `anonymous`
- value:
  - `room_number`
  - `diet[]`, `allergies[]`, `likes[]`, `dislikes[]`
  - `history[]`: `{ts, message, extracted}`
  - `last_message_ts`

Mongo equivalent: `guest_profiles` with `_id = guest_key`.

Guest preferences are updated best-effort from every chat message (see `agent/concierge.py` + `services/guest_preference_service.py`).

---

## Tracing & logs

Every `/chat` request generates a short `trace_id` and logs structured JSON lines for service calls.

- Trace context: `utils/service_trace.py:trace_context()`
- Logging: `utils/service_trace.py:log_service_call()`

You can use the returned `trace_id` from the `/chat` response to correlate logs for debugging.

---

## Troubleshooting

- **Backend starts but responses fail**: check Ollama is running and `OLLAMA_MODEL` exists locally.
- **Mongo enabled but writes fail**: confirm MongoDB is reachable at `MONGO_URI`.
- **Local recommendations say “not available”**: set `SERPER_API_KEY` or use broad categories (restaurants/cafes/tourist places) for JSON fallback.
- **Menu/hotel doc Q&A not working**: ensure PDFs exist in `data/docs/` and run `python scripts/build_rag_index.py`.
- **PowerShell encoding odd characters**: logs and some data files may show mojibake if the console encoding differs; the tracer uses `ensure_ascii=True` to reduce this.

---

## Example prompts to try

- “What time is breakfast?”
- “What’s the Wi‑Fi policy?”
- “Send coffee to room 204”
- “I’m vegan and allergic to peanuts”
- “I want to complain: the AC in room 204 is not working (maintenance, high severity, location room)”
- “What’s the status of ticket CMP-XXXXXXXXXX?”
- “Recommend restaurants nearby” (set `SERPER_API_KEY` for best results)
#   H o t e l _ A s s i s t a n t  
 