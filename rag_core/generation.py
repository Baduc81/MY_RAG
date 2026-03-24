"""
Generation module: LLM-powered answer generation from retrieved chunks.
"""

from __future__ import annotations

import json
from typing import List

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

from rag_core import config


def _build_answer_prompt(query: str, chunks: List[Document]) -> str:
    prompt = (
        f"Based on the following documents, please answer this question: {query}\n\n"
        "CONTENT TO ANALYZE:\n"
    )

    for i, chunk in enumerate(chunks):
        prompt += f"--- Document {i + 1} ---\n"

        if "original_content" in chunk.metadata:
            original = json.loads(chunk.metadata["original_content"])

            raw_text = original.get("raw_text", "")
            if raw_text:
                prompt += f"TEXT:\n{raw_text}\n\n"

            tables_html = original.get("tables_html", [])
            if tables_html:
                prompt += "TABLES:\n"
                for j, table in enumerate(tables_html):
                    prompt += f"Table {j + 1}:\n{table}\n\n"
        else:
            prompt += f"{chunk.page_content}\n\n"

        prompt += "\n"

    prompt += (
        "Please provide a clear, comprehensive answer using the text and tables above. "
        "If the documents don't contain sufficient information to answer the question, "
        'say "I don\'t have enough information to answer that question based on the '
        'provided documents."\n\nANSWER:'
    )
    return prompt


def generate_answer(query: str, chunks: List[Document]) -> str:
    """
    Generate a natural-language answer for *query* using *chunks* as context.

    Parameters
    ----------
    query:  The user's question.
    chunks: Retrieved document chunks (from retrieval.retrieve).

    Returns
    -------
    The LLM-generated answer string.
    """
    if not chunks:
        return (
            "I don't have enough information to answer that question "
            "based on the provided documents."
        )

    llm = ChatOllama(
        model=config.TEXT_MODEL,
        temperature=0,
        base_url=config.OLLAMA_BASE_URL,
    )

    prompt_text = _build_answer_prompt(query, chunks)
    message = HumanMessage(content=[{"type": "text", "text": prompt_text}])

    try:
        response = llm.invoke([message])
        return response.content
    except Exception as exc:
        print(f"Answer generation failed: {exc}")
        return "Sorry, I encountered an error while generating the answer."
