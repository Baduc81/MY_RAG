"""
Pipeline wrapper: end-to-end RAG flow.

Usage
-----
from rag_core.pipeline import ingest_file, ask

ingest_file("/path/to/document.pdf")
answer = ask("What is this document about?")
"""

from __future__ import annotations

import json

from rag_core import config
from rag_core.generation import generate_answer
from rag_core.ingestion import (
    add_documents_to_store,
    create_chunks_by_title,
    get_embedding_model,
    is_file_already_ingested,
    partition_document,
    save_ingested_file,
    summarize_chunks,
)
from rag_core.retrieval import retrieve


def _extract_chunk_debug_info(chunks: list) -> list[dict]:
    """Return a JSON-serializable view of retrieved chunks used for generation."""
    context_chunks: list[dict] = []

    for idx, chunk in enumerate(chunks, start=1):
        source_file = chunk.metadata.get("source_file") if chunk.metadata else None
        raw_text = chunk.page_content
        tables_html: list = []
        has_images = False

        if chunk.metadata and "original_content" in chunk.metadata:
            try:
                original = json.loads(chunk.metadata["original_content"])
                raw_text = original.get("raw_text", raw_text)
                tables_html = original.get("tables_html", [])
                has_images = bool(original.get("images_base64", []))
            except Exception:
                # Keep fallback values if metadata payload cannot be decoded.
                pass

        context_chunks.append(
            {
                "index": idx,
                "source_file": source_file,
                "text": raw_text,
                "tables_html": tables_html,
                "has_images": has_images,
            }
        )

    return context_chunks


def ingest_file(file_path: str, force: bool = False) -> dict:
    """
    Run the complete ingestion pipeline for a single file.

    Parameters
    ----------
    file_path:  Absolute path to the document to ingest.
    force:      Re-ingest even if the file has already been processed.

    Returns
    -------
    A dict with keys: ``source_file``, ``skipped``, ``chunks_added``.
    """
    import os

    source_file = os.path.basename(file_path)

    if not force and is_file_already_ingested(source_file):
        print(f"Skipping '{source_file}': already ingested.")
        return {"source_file": source_file, "skipped": True, "chunks_added": 0}

    print(f"Starting ingestion pipeline for '{source_file}'...")

    elements = partition_document(file_path)
    chunks = create_chunks_by_title(elements)
    documents = summarize_chunks(chunks, source_file=source_file)

    embedding_model = get_embedding_model()
    add_documents_to_store(documents, embedding_model=embedding_model)

    save_ingested_file(source_file)

    print(f"Ingestion complete: {len(documents)} chunks stored for '{source_file}'.")
    return {
        "source_file": source_file,
        "skipped": False,
        "chunks_added": len(documents),
    }


def ask(query: str, k: int = 5) -> str:
    """
    Run the retrieval + generation pipeline for a user question.

    Parameters
    ----------
    query:  The user's natural-language question.
    k:      Number of document chunks to retrieve.

    Returns
    -------
    The generated answer string.
    """
    chunks = retrieve(query, k=k)
    return generate_answer(query, chunks)


def ask_with_context(query: str, k: int = 5) -> dict:
    """Run retrieval + generation and return answer with the chunks used."""
    chunks = retrieve(query, k=k)
    answer = generate_answer(query, chunks)
    return {
        "answer": answer,
        "context_chunks": _extract_chunk_debug_info(chunks),
    }
