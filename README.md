# RAG Assistant — Local-First Web UI

A fully local, containerised **Retrieval-Augmented Generation (RAG)** system with a
modern dark-theme chat UI. All AI inference is performed through
[Ollama](https://ollama.com) running on your machine — no cloud dependencies required.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Browser                                            │
│  React + Vite (dark theme, ChatGPT-style UI)        │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP / nginx proxy
┌──────────────────────▼──────────────────────────────┐
│  Backend  (FastAPI, port 8000)                      │
│  /api/upload  /api/chat  /api/documents  /api/reset │
└───────────┬──────────────────────┬──────────────────┘
            │                      │
┌───────────▼──────┐   ┌───────────▼──────────────────┐
│  Qdrant          │   │  Ollama (host machine)        │
│  Vector DB       │   │  • nomic-embed-text           │
│  port 6333       │   │  • qwen2.5:7b-instruct        │
└──────────────────┘   │  • llama3.2-vision:11b (opt.) │
                       └──────────────────────────────┘
```

### RAG Core modules (`rag_core/`)

| Module | Responsibility |
|---|---|
| `config.py` | Environment-variable configuration |
| `ingestion.py` | Document partitioning, chunking, AI summarisation, Qdrant storage |
| `retrieval.py` | Vector similarity search |
| `generation.py` | LLM answer generation |
| `pipeline.py` | End-to-end `ingest_file()` and `ask()` helpers |

---

## Prerequisites

| Tool | Purpose |
|---|---|
| [Docker + Docker Compose](https://docs.docker.com/get-docker/) | Run all services |
| [Ollama](https://ollama.com) | Local LLM inference (runs on your host) |

### Pull required Ollama models

```bash
ollama pull nomic-embed-text          # embeddings (required)
ollama pull qwen2.5:7b-instruct       # text generation (required)
ollama pull llama3.2-vision:11b       # vision (optional, see ENABLE_VISION)
```

---

## Quick Start

```bash
# 1. Clone & enter the repo
git clone https://github.com/Baduc81/MY_RAG.git
cd MY_RAG

# 2. Copy and (optionally) edit environment variables
cp .env.example .env

# 3. Build and start all services
docker compose up --build

# 4. Open the UI
open http://localhost:3000
```

The first time, Docker builds the backend image (downloading ~2 GB of
Python/system deps). Subsequent starts are fast.

---

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama API endpoint |
| `TEXT_MODEL` | `qwen2.5:7b-instruct` | Model used for answer generation |
| `VISION_MODEL` | `llama3.2-vision:11b` | Model used for image summarisation |
| `EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `ENABLE_VISION` | `false` | Set `true` to enable multimodal PDF summarisation |
| `COLLECTION_NAME` | `rag_docs` | Qdrant collection name |

---

## Supported File Types

`.pdf` · `.csv` · `.docx` · `.doc` · `.txt`

---

## Data Persistence

Two Docker named volumes persist data between restarts:

| Volume | Contents |
|---|---|
| `uploads` | Uploaded files + ingest tracker JSON |
| `qdrant_storage` | Qdrant vector database |

To wipe all data:

```bash
docker compose down -v   # removes volumes
```

Or use the **Reset** button in the UI → `POST /api/reset`.

---

## Development (without Docker)

```bash
# Backend
cd /path/to/MY_RAG
pip install -r backend/requirements.txt

# Set env vars
export OLLAMA_BASE_URL=http://localhost:11434
export QDRANT_URL=http://localhost:6333
export UPLOADS_DIR=/tmp/rag-uploads
export INGEST_TRACKING_FILE=/tmp/rag-uploads/ingested_files.json

uvicorn backend.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev   # opens http://localhost:5173 with /api proxy to :8000
```
