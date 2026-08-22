import logging
from typing import List, Dict, Any, Optional

from sentence_transformers import CrossEncoder

reranker_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def _evidence_text(chunk: Dict[str, Any]) -> str:
    meta = chunk.get("metadata", {}) or {}
    parts = [
        str(meta.get("filename", "")),
        str(meta.get("heading", "")),
        str(meta.get("content_type", "")),
        str(meta.get("source_type", "")),
        str(chunk.get("text", "")),
    ]
    return " | ".join(p for p in parts if p).strip()


def rerank_chunks(
    question: str,
    chunks: List[Dict[str, Any]],
    scope: str = "adaptive",
    query_variants: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Rank evidence using the question plus planner-generated semantic formulations.

    No document names, question types, per-document quotas, or fixed final chunk counts
    are used. Metadata is included in the reranker representation so table/diagram
    chunks can be distinguished from unrelated prose.
    """
    if not chunks:
        return []

    queries = [str(question).strip()]
    for q in query_variants or []:
        q = str(q).strip()
        if q and q not in queries:
            queries.append(q)

    # Score each candidate against the strongest formulation.
    # CrossEncoder scores are kept per candidate for downstream adaptive selection.
    pairs = []
    candidate_query_index = []
    for chunk in chunks:
        evidence = _evidence_text(chunk)
        for q in queries:
            pairs.append([q, evidence])
        candidate_query_index.append(len(queries))

    try:
        raw_scores = reranker_model.predict(pairs)
    except Exception as exc:
        logging.error("Error during CrossEncoder reranking: %s", exc)
        for chunk in chunks:
            item = dict(chunk)
            item["rerank_score"] = None
            item["matched_queries"] = queries
            yield_item = item
            # Preserve caller behavior below by attaching directly.
            chunk["_rerank_fallback"] = yield_item
        return [c["_rerank_fallback"] for c in chunks]

    ranked = []
    width = len(queries)
    for idx, chunk in enumerate(chunks):
        scores = [float(x) for x in raw_scores[idx * width:(idx + 1) * width]]
        best_idx = max(range(len(scores)), key=lambda i: scores[i])
        item = dict(chunk)
        item["rerank_score"] = scores[best_idx]
        item["matched_query"] = queries[best_idx]
        item["rerank_scores"] = scores
        ranked.append(item)

    ranked.sort(key=lambda x: x.get("rerank_score", float("-inf")), reverse=True)
    return ranked
