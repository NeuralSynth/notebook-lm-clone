# NotebookLM Clone — RAG Document Chat

A full RAG pipeline that lets you upload documents and have a grounded conversation with them. Built for SST Assignment 03.

## Stack

| Layer      | Technology                      |
|------------|---------------------------------|
| Frontend   | React + Vite                    |
| Backend    | FastAPI (Python)                |
| Embeddings | OpenAI `text-embedding-3-large` |
| Vector DB  | Qdrant Cloud                    |
| LLM        | Gemini 1.5 Flash (streamed)     |
| Infra      | Docker + Docker Compose         |

## RAG Pipeline

```
PDF/TXT upload
    → parse (PyMuPDF / UTF-8 decode)
    → chunk  (fixed-size 2000 chars, 200 char overlap, sentence-boundary snapping)
    → embed  (OpenAI text-embedding-3-large → 3072-dim vectors)
    → store  (Qdrant Cloud, cosine similarity, doc_id metadata)

User query
    → embed query (same model)
    → retrieve top-6 chunks (cosine search, optionally filtered by doc_id)
    → build context (source + page citations)
    → generate (Gemini 1.5 Flash, strict grounding prompt, streamed SSE)
```

### Chunking Strategy

See `backend/app/services/chunker.py` for full documentation.

- **Fixed-size with overlap**: 2000 character chunks, 200 character overlap so context is never lost at boundaries.
- **Sentence-boundary snapping**: After computing the raw cut point, the chunker walks back up to 100 characters to find the nearest sentence end (`.`, `!`, `?`) so chunks never cut mid-sentence.
- **Per-page chunking**: For PDFs, each page is chunked independently so page number metadata is preserved in every chunk and surfaced in citations.

## Architecture & Design Patterns

| Pattern | Implementation | Purpose |
|---------|---------------|---------|
| **Settings Pattern** | `app/config.py` | Centralized, validated config via `pydantic-settings` |
| **Repository Pattern** | `app/repositories/vector_store.py` | Abstracts Qdrant operations behind a clean interface |
| **Service Layer** | `app/services/ingest.py`, `query.py` | Business logic separated from HTTP handlers |
| **Dependency Injection** | `app/dependencies.py` + FastAPI `Depends()` | Loose coupling, testability |
| **Singleton (Lifespan)** | `app/clients.py` + app lifespan | Clients created once, shared across requests |
| **App Factory** | `app/main.py` → `create_app()` | Configurable app creation |

## Local Setup

### Prerequisites
- Docker & Docker Compose
- OpenAI API key
- Gemini API key ([aistudio.google.com](https://aistudio.google.com))
- Qdrant Cloud account ([cloud.qdrant.io](https://cloud.qdrant.io)) — free tier is sufficient

### Run (Docker — Production)

```bash
git clone <repo-url>
cd notebooklm-clone

cp .env.example .env
# Fill in your API keys in .env

docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000).

### Run (Docker — Development with live reload)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Without Docker (dev mode)

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill keys
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev   # runs on :3000, proxies /api to :8000
```

## Deployment

- **Backend** → Render (point at `backend/Dockerfile`, set env vars in Render dashboard)
- **Frontend** → Vercel (set `VITE_API_URL=https://your-render-backend.onrender.com` in Vercel env vars)

### Production Checklist
- [ ] Set `ALLOWED_ORIGINS` to your Vercel URL in backend env vars
- [ ] Set `VITE_API_URL` to your Render backend URL in Vercel env vars
- [ ] Verify all 4 API keys are set
- [ ] Test `docker compose up --build` end-to-end before deploying

## Project Structure

```
notebooklm-clone/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # App factory, lifespan, middleware
│   │   ├── config.py             # Settings (pydantic-settings)
│   │   ├── clients.py            # Singleton client manager
│   │   ├── dependencies.py       # FastAPI DI wiring
│   │   ├── exceptions.py         # Custom exceptions + handlers
│   │   ├── routes/
│   │   │   ├── health.py         # GET /api/health
│   │   │   ├── documents.py      # Upload, list, delete
│   │   │   └── chat.py           # SSE streaming chat
│   │   ├── services/
│   │   │   ├── ingest.py         # Parse → chunk → embed → store
│   │   │   ├── query.py          # Embed → retrieve → generate
│   │   │   └── chunker.py        # Chunking strategy
│   │   ├── repositories/
│   │   │   └── vector_store.py   # Qdrant abstraction
│   │   └── schemas/
│   │       └── models.py         # Pydantic request/response models
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   └── components/
│   │       ├── Upload.jsx
│   │       ├── DocumentList.jsx
│   │       └── Chat.jsx
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml          # Production
├── docker-compose.dev.yml      # Development override
└── .env.example
```
