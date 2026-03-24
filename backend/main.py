"""
FastAPI backend for the local RAG web UI.

Endpoints
---------
GET  /api/health            Liveness check
GET  /api/documents         List ingested documents
POST /api/upload            Upload + ingest one or more files
DELETE /api/documents/{fn}  Remove a document from the store
POST /api/chat              Ask a question
POST /api/reset             Wipe all data
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure rag_core is importable (it lives one level up from /app/backend)
import sys

sys.path.insert(0, "/app")

from rag_core import config
from rag_core.ingestion import (
    load_ingested_files,
    remove_ingested_file,
    reset_vector_store,
)
from rag_core.pipeline import ask, ingest_file

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOADS_DIR = Path(config.UPLOADS_DIR)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    query: str
    k: int = 5


class ChatResponse(BaseModel):
    answer: str


class DocumentInfo(BaseModel):
    filename: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/documents", response_model=List[DocumentInfo])
def list_documents():
    """Return all documents that have been ingested."""
    files = load_ingested_files()
    return [{"filename": f} for f in sorted(files)]


@app.post("/api/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
):
    """
    Save uploaded files to disk and run the ingestion pipeline.
    The response is returned only after indexing completes so the
    frontend can block the chat until the documents are ready.
    """
    results = []
    for upload in files:
        filename = upload.filename or "upload"
        ext = Path(filename).suffix.lower()
        if ext not in config.SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported file type '{ext}'. "
                    f"Supported: {', '.join(sorted(config.SUPPORTED_EXTENSIONS))}"
                ),
            )

        dest = UPLOADS_DIR / filename
        with dest.open("wb") as f:
            shutil.copyfileobj(upload.file, f)

        result = ingest_file(str(dest))
        results.append(result)

    return {"results": results}


@app.delete("/api/documents/{filename}")
def delete_document(filename: str):
    """
    Remove a document from the ingest tracker and disk.

    Note: embeddings already stored in Qdrant are NOT deleted because Qdrant
    does not natively support filtering deletions by metadata field without
    scrolling and collecting IDs, which is an expensive O(n) operation.
    To fully purge all vectors, use POST /api/reset instead.
    """
    # Remove from tracker
    remove_ingested_file(filename)

    # Remove file from disk if it exists
    dest = UPLOADS_DIR / filename
    if dest.exists():
        dest.unlink()

    return {"deleted": filename}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Query the RAG pipeline and return an answer."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    ingested = load_ingested_files()
    if not ingested:
        raise HTTPException(
            status_code=400,
            detail="No documents have been uploaded yet. Please upload documents first.",
        )

    answer = ask(request.query, k=request.k)
    return {"answer": answer}


@app.post("/api/reset")
def reset():
    """Delete all vectors and ingestion records."""
    reset_vector_store()
    return {"status": "reset complete"}
