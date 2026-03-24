"""
Ingestion module: document loading, chunking, AI summarisation, and vector storage.

This module is extracted from final.ipynb and adapted for use as a plain Python
module — no Jupyter runtime is required.
"""

from __future__ import annotations

import json
import os
import time
from typing import List

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from unstructured.chunking.title import chunk_by_title
from unstructured.partition.auto import partition
from unstructured.partition.pdf import partition_pdf

from rag_core import config

# ---------------------------------------------------------------------------
# Embedding model (module-level singleton — re-used across calls)
# ---------------------------------------------------------------------------

def get_embedding_model() -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=config.EMBED_MODEL,
        base_url=config.OLLAMA_BASE_URL,
    )


# ---------------------------------------------------------------------------
# Ingested-files tracker
# ---------------------------------------------------------------------------

def load_ingested_files(tracking_file: str = config.INGEST_TRACKING_FILE) -> set:
    """Return the set of already-ingested filenames."""
    if not os.path.exists(tracking_file):
        return set()
    try:
        with open(tracking_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return set(data)
    except Exception as e:
        print(f"Warning: cannot read {tracking_file}: {e}")
    return set()


def save_ingested_file(
    source_file: str,
    tracking_file: str = config.INGEST_TRACKING_FILE,
) -> None:
    """Persist a newly ingested filename to the local tracker."""
    files = load_ingested_files(tracking_file)
    files.add(source_file)
    os.makedirs(os.path.dirname(tracking_file), exist_ok=True)
    with open(tracking_file, "w", encoding="utf-8") as f:
        json.dump(sorted(files), f, indent=2, ensure_ascii=False)


def is_file_already_ingested(
    source_file: str,
    tracking_file: str = config.INGEST_TRACKING_FILE,
) -> bool:
    return source_file in load_ingested_files(tracking_file)


def remove_ingested_file(
    source_file: str,
    tracking_file: str = config.INGEST_TRACKING_FILE,
) -> None:
    """Remove a filename from the ingest tracker."""
    files = load_ingested_files(tracking_file)
    files.discard(source_file)
    os.makedirs(os.path.dirname(tracking_file), exist_ok=True)
    with open(tracking_file, "w", encoding="utf-8") as f:
        json.dump(sorted(files), f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Document partitioning
# ---------------------------------------------------------------------------

def partition_document(file_path: str) -> list:
    """Extract elements from supported document formats."""
    extension = os.path.splitext(file_path)[1].lower()
    if extension not in config.SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {extension}. "
            f"Supported types: {', '.join(sorted(config.SUPPORTED_EXTENSIONS))}"
        )

    print(f"Partitioning document: {file_path}")

    if extension == ".pdf":
        elements = partition_pdf(
            filename=file_path,
            strategy="hi_res",
            infer_table_structure=True,
            extract_image_block_type=["Image"],
            extract_image_block_to_payload=True,
            extract_images_in_pdf=True,
        )
    else:
        elements = partition(filename=file_path)

    print(f"Extracted {len(elements)} elements.")
    return elements


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def create_chunks_by_title(elements: list) -> list:
    """Create intelligent title-based chunks."""
    print("Chunking by title...")
    chunks = chunk_by_title(
        elements=elements,
        max_characters=3000,
        new_after_n_chars=2400,
        combine_text_under_n_chars=500,
    )
    print(f"Created {len(chunks)} chunks.")
    return chunks


# ---------------------------------------------------------------------------
# Content separation helpers
# ---------------------------------------------------------------------------

def separate_content_types(chunk) -> dict:
    """Separate text, tables, and images from a chunk element."""
    content_data: dict = {
        "text": chunk.text,
        "tables": [],
        "images": [],
        "types": ["text"],
    }

    if hasattr(chunk, "metadata") and hasattr(chunk.metadata, "orig_elements"):
        for element in chunk.metadata.orig_elements:
            element_type = type(element).__name__

            if element_type == "Table":
                content_data["types"].append("table")
                table_html = getattr(element.metadata, "text_as_html", element.text)
                content_data["tables"].append(table_html)

            elif element_type == "Image":
                if hasattr(element, "metadata") and hasattr(
                    element.metadata, "image_base64"
                ):
                    content_data["types"].append("image")
                    content_data["images"].append(element.metadata.image_base64)

    content_data["types"] = list(set(content_data["types"]))
    return content_data


# ---------------------------------------------------------------------------
# AI Summarisation helpers
# ---------------------------------------------------------------------------

def _build_summary_prompt(text: str, tables: list, image_count: int) -> str:
    prompt = f"""You are creating a searchable description for document retrieval.

CONTENT TO ANALYZE:
TEXT CONTENT:
{text}

YOUR TASK:
Generate a comprehensive, searchable description that covers:
1. Key facts, numbers, and data points from text and tables
2. Main topics and concepts discussed
3. Questions this content could answer
4. Alternative search terms users might use
5. If visual information exists, include likely chart/diagram intent

Prioritize findability over brevity.
"""
    if tables:
        prompt += "\n\nTABLES:\n"
        for i, table in enumerate(tables, start=1):
            prompt += f"Table {i}:\n{table}\n\n"

    if image_count > 0:
        prompt += f"\nThis chunk contains {image_count} image(s). Include visual context when possible.\n"

    prompt += "\nSEARCHABLE DESCRIPTION:"
    return prompt


def _estimate_base64_size_mb(image_base64: str) -> float:
    if not image_base64:
        return 0.0
    return (len(image_base64) * 3 / 4) / (1024 * 1024)


def _prepare_images_for_vision(
    images: list,
    max_images: int = 1,
    max_image_mb: float = 1.5,
    max_total_mb: float = 2.0,
) -> list:
    selected: list = []
    total_mb = 0.0
    for img in images:
        if not img or not isinstance(img, str):
            continue
        img_mb = _estimate_base64_size_mb(img)
        if img_mb > max_image_mb:
            continue
        if total_mb + img_mb > max_total_mb:
            break
        selected.append(img)
        total_mb += img_mb
        if len(selected) >= max_images:
            break
    return selected


def _invoke_summary_model(
    model_name: str,
    prompt_text: str,
    images_base64: list,
    num_ctx: int,
    timeout: int,
) -> str:
    llm = ChatOllama(
        model=model_name,
        temperature=0,
        base_url=config.OLLAMA_BASE_URL,
        num_ctx=num_ctx,
        timeout=timeout,
        keep_alive=0,
    )
    message_content: list = [{"type": "text", "text": prompt_text}]
    for img in images_base64:
        message_content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img}"},
            }
        )
    response = llm.invoke([HumanMessage(content=message_content)])
    return response.content


def create_ai_summary(text: str, tables: list, images: list) -> dict:
    """Generate an AI summary for a chunk, with vision retry and text fallback."""
    prompt_text = _build_summary_prompt(text, tables, len(images))
    safe_images = _prepare_images_for_vision(images, max_images=1, max_image_mb=1.0, max_total_mb=1.0)
    use_vision = config.ENABLE_VISION and len(safe_images) > 0

    if use_vision:
        try:
            content = _invoke_summary_model(
                model_name=config.VISION_MODEL,
                prompt_text=prompt_text,
                images_base64=safe_images,
                num_ctx=2048,
                timeout=600,
            )
            return {"summary": content, "used_fallback": False, "model_used": config.VISION_MODEL}
        except Exception as e1:
            print(f"Vision attempt #1 failed: {e1}")
            try:
                content = _invoke_summary_model(
                    model_name=config.VISION_MODEL,
                    prompt_text=prompt_text,
                    images_base64=safe_images,
                    num_ctx=2048,
                    timeout=600,
                )
                return {"summary": content, "used_fallback": False, "model_used": config.VISION_MODEL}
            except Exception as e2:
                print(f"Vision attempt #2 failed: {e2}")

    try:
        text_only_prompt = _build_summary_prompt(text, tables, image_count=0)
        content = _invoke_summary_model(
            model_name=config.TEXT_MODEL,
            prompt_text=text_only_prompt,
            images_base64=[],
            num_ctx=3072,
            timeout=300,
        )
        return {"summary": content, "used_fallback": True, "model_used": config.TEXT_MODEL}
    except Exception as exc:
        print(f"Text fallback failed: {exc}")

    # Final local fallback
    summary = f"{text[:300]}..."
    if tables:
        summary += f" [Contains {len(tables)} table(s)]"
    if images:
        summary += f" [Contains {len(images)} image(s)]"
    return {"summary": summary, "used_fallback": True, "model_used": "local-fallback"}


def summarize_chunks(chunks: list, source_file: str) -> List[Document]:
    """Process all chunks with AI summarisation and return LangChain Documents."""
    print("Processing chunks with AI summarisation...")
    documents: List[Document] = []
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        print(f"Summarising chunk {i + 1}/{total}...")
        content_data = separate_content_types(chunk)

        if content_data["tables"] or content_data["images"]:
            result = create_ai_summary(
                content_data["text"],
                content_data["tables"],
                content_data["images"],
            )
            summary = result["summary"]
        else:
            summary = content_data["text"]

        doc = Document(
            page_content=summary,
            metadata={
                "source_file": source_file,
                "original_content": json.dumps(
                    {
                        "raw_text": content_data["text"],
                        "tables_html": content_data["tables"],
                        "images_base64": content_data["images"],
                    }
                ),
            },
        )
        documents.append(doc)

    print(f"Created {len(documents)} LangChain Documents.")
    return documents


# ---------------------------------------------------------------------------
# Vector store
# ---------------------------------------------------------------------------

def _ensure_collection_exists(
    client: QdrantClient,
    embedding_model: OllamaEmbeddings,
    collection_name: str,
) -> None:
    """Create the Qdrant collection if it does not already exist."""
    try:
        exists = client.collection_exists(collection_name=collection_name)
    except Exception:
        try:
            client.get_collection(collection_name=collection_name)
            exists = True
        except Exception:
            exists = False

    if exists:
        return

    vector_dim = len(embedding_model.embed_query("dimension_probe"))
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_dim, distance=Distance.COSINE),
    )
    print(f"Created Qdrant collection '{collection_name}' (dim={vector_dim}).")


def get_vector_store(
    embedding_model: OllamaEmbeddings | None = None,
) -> QdrantVectorStore:
    """Return a QdrantVectorStore connected to the configured collection."""
    if embedding_model is None:
        embedding_model = get_embedding_model()

    client = QdrantClient(url=config.QDRANT_URL, timeout=10)
    _ensure_collection_exists(client, embedding_model, config.COLLECTION_NAME)
    return QdrantVectorStore(
        client=client,
        collection_name=config.COLLECTION_NAME,
        embedding=embedding_model,
    )


def add_documents_to_store(
    documents: List[Document],
    embedding_model: OllamaEmbeddings | None = None,
) -> QdrantVectorStore:
    """Embed and store documents; return the vector store."""
    if embedding_model is None:
        embedding_model = get_embedding_model()

    store = get_vector_store(embedding_model)
    if documents:
        store.add_documents(documents)
        print(f"Added {len(documents)} documents to Qdrant.")
    return store


def reset_vector_store(
    tracking_file: str = config.INGEST_TRACKING_FILE,
) -> None:
    """Delete the Qdrant collection and reset the ingest tracker."""
    client = QdrantClient(url=config.QDRANT_URL, timeout=10)
    try:
        client.delete_collection(collection_name=config.COLLECTION_NAME)
        print(f"Deleted collection: {config.COLLECTION_NAME}")
    except Exception as e:
        print(f"Collection delete skipped: {e}")

    os.makedirs(os.path.dirname(tracking_file), exist_ok=True)
    with open(tracking_file, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)
    print("Reset ingest tracker.")
