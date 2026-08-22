import logging
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"


def clean_query_for_retrieval(query: str) -> str:
    """
    Preserve the user's retrieval intent.

    This function intentionally performs only harmless whitespace normalization.
    Scope phrases such as 'both documents', 'across documents', and 'uploaded files'
    can determine evidence coverage and must never be removed.
    """
    q = " ".join(str(query).strip().split())
    return q


def rewrite_query(question: str) -> str:
    """
    Produce an optional search formulation while preserving the original question.
    This function is kept for backward compatibility; the planner is the primary
    retrieval-planning component.
    """
    original = clean_query_for_retrieval(question)
    if len(original) < 3:
        return question

    prompt = f"""Rewrite this question into one concise semantic search query.
Preserve every important entity, relationship, comparison target, scope qualifier,
and document-reference phrase. Do not remove phrases such as 'both documents' or
'across the uploaded documents'. Return only the query.

Question: {original}
"""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0},
            },
            timeout=8,
        )
        response.raise_for_status()
        rewritten = response.json().get("response", "").strip().strip('"\'')
        return rewritten if len(rewritten) >= 3 else original
    except Exception as exc:
        logging.warning("Query rewriting fallback (%s). Using original query.", exc)
        return original
