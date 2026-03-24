"""
Configuration for the RAG core pipeline.
All values are read from environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Ollama
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
TEXT_MODEL: str = os.getenv("TEXT_MODEL", "qwen2.5:7b-instruct")
VISION_MODEL: str = os.getenv("VISION_MODEL", "llama3.2-vision:11b")
EMBED_MODEL: str = os.getenv("EMBED_MODEL", "nomic-embed-text")
ENABLE_VISION: bool = os.getenv("ENABLE_VISION", "false").lower() == "true"

# Qdrant
QDRANT_URL: str = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "rag_docs")

# File storage
UPLOADS_DIR: str = os.getenv("UPLOADS_DIR", "/app/uploads")
INGEST_TRACKING_FILE: str = os.getenv(
    "INGEST_TRACKING_FILE", "/app/uploads/ingested_files.json"
)

# Supported file extensions (must match partition_document logic)
SUPPORTED_EXTENSIONS: set = {".pdf", ".csv", ".docx", ".doc", ".txt"}
