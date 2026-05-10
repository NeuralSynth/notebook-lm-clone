# NotebookLM Clone - RAG Document Chat

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

See `backend/chunker.py` for full documentation.

- **Fixed-size with overlap**: 2000 character chunks, 200 character overlap so context is never lost at boundaries.
- **Sentence-boundary snapping**: After computing the raw cut point, the chunker walks back up to 100 characters to find the nearest sentence end (`.`, `!`, `?`) so chunks never cut mid-sentence.
- **Per-page chunking**: For PDFs, each page is chunked independently so page number metadata is preserved in every chunk and surfaced in citations.

## Local Setup

### Prerequisites
- Docker & Docker Compose
- OpenAI API key
- Gemini API key ([aistudio.google.com](https://aistudio.google.com))
- Qdrant Cloud account ([cloud.qdrant.io](https://cloud.qdrant.io)) — free tier is sufficient

### Run

```bash
git clone https://github.com/NeuralSynth/notebook-lm-clone
cd notebook-lm-clone

cp .env.example .env
# Fill in your API keys in .env

docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000).

### Without Docker (dev mode)

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill keys
uvicorn main:app --reload --port 8000
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

## Project Structure

```
notebooklm-clone/
├── backend/
│   ├── main.py        # FastAPI routes
│   ├── ingest.py      # parse → chunk → embed → upsert
│   ├── query.py       # embed → retrieve → generate (streamed)
│   ├── chunker.py     # chunking strategy (documented)
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
├── docker-compose.yml
└── .env.example
```
