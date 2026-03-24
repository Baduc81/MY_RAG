"""
Pytest configuration: mock heavy rag_core dependencies before importing the app
so that tests can run without Ollama, Qdrant, or any ML libraries installed.
"""

import os
import sys
from unittest.mock import MagicMock

# Add the backend directory to sys.path so tests can do `from main import app`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# --- Minimal stubs for rag_core submodules ---------------------------------

_config = MagicMock()
_config.UPLOADS_DIR = "/tmp/test-rag-uploads"
_config.SUPPORTED_EXTENSIONS = {".pdf", ".csv", ".docx", ".doc", ".txt"}

_ingestion = MagicMock()
_ingestion.load_ingested_files.return_value = []
_ingestion.remove_ingested_file.return_value = None
_ingestion.reset_vector_store.return_value = None

_pipeline = MagicMock()
_pipeline.ask.return_value = "Mock answer"
_pipeline.ask_with_context.return_value = {
    "answer": "Mock answer",
    "context_chunks": [
        {
            "index": 1,
            "source_file": "test.pdf",
            "text": "Mock chunk text",
            "tables_html": [],
            "has_images": False,
        }
    ],
}
_pipeline.ingest_file.return_value = {
    "source_file": "test.pdf",
    "skipped": False,
    "chunks_added": 5,
}

_rag_core = MagicMock()
_rag_core.config = _config

# Register mocks before any import of backend.main triggers real imports
sys.modules["rag_core"] = _rag_core
sys.modules["rag_core.config"] = _config
sys.modules["rag_core.ingestion"] = _ingestion
sys.modules["rag_core.pipeline"] = _pipeline
