import re
import logging
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"


def clean_query_for_retrieval(query: str) -> str:
    """
    Strips meta-document phrases (e.g. 'across both uploaded documents')
    that degrade semantic vector embeddings and cross-encoders.
    """
    q = query
    meta_patterns = [
        r"\b(across|in|from|between|of)\s+(both|all|the|my|these|our)\s+(uploaded\s+)?(documents?|files?|pdfs?)\b",
        r"\b(in|from)\s+(the|both|all)\s+(uploaded\s+)?(documents?|files?|pdfs?)\b",
        r"\b(across|in)\s+both\s+(documents?|files?|pdfs?)\b",
        r"\b(uploaded\s+)?(documents?|files?|pdfs?)\b"
    ]
    for p in meta_patterns:
        q = re.sub(p, "", q, flags=re.IGNORECASE)
    q = re.sub(r"\s+", " ", q).strip()
    return q if len(q) >= 3 else query


def rewrite_query(question: str) -> str:
    """
    Cleans and refines user query for optimal dense retrieval.
    """
    # First apply rule-based meta-cleaner
    cleaned = clean_query_for_retrieval(question)

    # For comparative questions or well-formed questions, return cleaned directly
    if any(k in question.lower() for k in ["compare", "difference", "vs", "versus", "both", "across", "summarize", "overview"]):
        return cleaned

    prompt = f"""Rewrite the question into a concise search query. Return ONLY the search query text with no boolean operators, no quotes, and no preamble.

Question: {cleaned}
Search query:"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0
                }
            },
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            rewritten = result.get("response", "").strip().strip('"\'')
            # Ensure the rewritten query is reasonable
            if rewritten and len(rewritten) > 2 and not any(op in rewritten for op in [" AND ", " OR ", " NOT "]):
                return rewritten
    except Exception as e:
        logging.warning(f"Query rewriting fallback ({e}). Using cleaned query.")

    return cleaned