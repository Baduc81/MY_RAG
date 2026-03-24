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
│  Qdrant          │   │  Ollama (host machine)       │
│  Vector DB       │   │  • nomic-embed-text          │
│  port 6333       │   │  • qwen2.5:7b-instruct       │
└──────────────────┘   │  • llama3.2-vision:11b (opt.)│
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

## Deploy on AWS EC2 (Docker)

This repo includes an EC2 override file: `docker-compose.ec2.yml`.
It adds an `ollama` container so you can run the full stack on EC2 with Docker.

### 1. Launch EC2 instance

- Recommended minimum: `t3.large` (CPU-only, slow inference) or GPU instance for better speed.
- Open Security Group ports:
- `22` (SSH)
- `3000` (frontend)
- Optional `8000` only if you need direct backend access.

### 2. Install Docker on EC2 (Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

### 3. Start services

```bash
git clone https://github.com/Baduc81/MY_RAG.git
cd MY_RAG

cp .env.example .env

# Run base compose + EC2 override
docker compose -f docker-compose.yml -f docker-compose.ec2.yml up -d --build
```

### 4. Pull Ollama models inside container

```bash
docker compose -f docker-compose.yml -f docker-compose.ec2.yml exec ollama ollama pull nomic-embed-text
docker compose -f docker-compose.yml -f docker-compose.ec2.yml exec ollama ollama pull qwen2.5:7b-instruct

# Optional vision model (large)
docker compose -f docker-compose.yml -f docker-compose.ec2.yml exec ollama ollama pull llama3.2-vision:11b
```

### 5. Verify

```bash
docker compose -f docker-compose.yml -f docker-compose.ec2.yml ps
curl http://localhost:8000/api/health
```

Open UI in browser:

```text
http://<EC2_PUBLIC_IP>:3000
```

### Notes

- CPU EC2 can run but may be slow for larger models.
- For GPU EC2, install NVIDIA driver + NVIDIA Container Toolkit, then uncomment `gpus: all` in `docker-compose.ec2.yml`.
- Model files are persisted in Docker volume `ollama_models`.

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
| `ollama_models` | Ollama model weights (when using EC2 override) |

To wipe all data:

```bash
docker compose down -v   # removes volumes
```

Or use the **Reset** button in the UI → `POST /api/reset`.

---

## Development (without Docker)

```bash
# Terminal 1: Qdrant (nếu chưa cài local thì chạy bằng docker riêng)
docker run -p 6333:6333 qdrant/qdrant

# Terminal 2: Backend local
cd /home/luminous/Project/Rag-for-beginner/MY_RAG
pip install -r backend/requirements.txt

# Sửa .env thành localhost (hoặc tạm đổi tên .env)
# OLLAMA_BASE_URL=http://localhost:11434

export QDRANT_URL=http://localhost:6333
export UPLOADS_DIR=/tmp/rag-uploads
export INGEST_TRACKING_FILE=/tmp/rag-uploads/ingested_files.json
export OLLAMA_BASE_URL=http://localhost:11434
uvicorn backend.main:app --reload --port 8000

# Terminal 3:
ollama serve

# Terminal 4: Frontend
cd frontend
npm install
npm run dev
```
