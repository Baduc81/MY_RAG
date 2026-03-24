"""
Basic API endpoint tests for the FastAPI backend.

All rag_core dependencies are mocked via conftest.py so that no external
services (Ollama, Qdrant) are required.
"""

import io

from fastapi.testclient import TestClient

from main import app  # conftest.py sets up sys.path and mocks before this import

client = TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------


def test_list_documents_empty():
    response = client.get("/api/documents")
    assert response.status_code == 200
    assert response.json() == []


def test_delete_document():
    response = client.delete("/api/documents/sample.pdf")
    assert response.status_code == 200
    assert response.json() == {"deleted": "sample.pdf"}


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


def test_upload_unsupported_file_type():
    response = client.post(
        "/api/upload",
        files=[("files", ("report.xyz", io.BytesIO(b"dummy"), "application/octet-stream"))],
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


def test_chat_empty_query():
    response = client.post("/api/chat", json={"query": ""})
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_chat_no_documents_uploaded():
    """Returns 400 when no documents have been ingested yet."""
    response = client.post("/api/chat", json={"query": "What is the document about?"})
    assert response.status_code == 400
    assert "No documents" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


def test_reset():
    response = client.post("/api/reset")
    assert response.status_code == 200
    assert response.json() == {"status": "reset complete"}
