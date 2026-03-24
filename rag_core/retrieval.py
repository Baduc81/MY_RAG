"""
Retrieval module: vector similarity search against the Qdrant store.
"""

from __future__ import annotations

from typing import List

from langchain_core.documents import Document

from rag_core.ingestion import get_embedding_model, get_vector_store


def retrieve(query: str, k: int = 5) -> List[Document]:
    """Return the top-k most relevant documents for *query*."""
    embedding_model = get_embedding_model()
    store = get_vector_store(embedding_model)
    retriever = store.as_retriever(search_kwargs={"k": k})
    results = retriever.invoke(query)
    print(f"Retrieved {len(results)} chunks for query: {query!r}")
    return results
