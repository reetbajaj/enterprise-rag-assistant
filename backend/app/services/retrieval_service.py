import logging
import math
from typing import List, Dict, Any, Optional

from app.services.vector_store import collection
from app.services.embedding_service import model
from app.services.reranker_service import rerank_chunks
from app.services.evidence_evaluator import evaluate_evidence_sufficiency
from app.services.query_planner import generate_retrieval_plan


def _candidate_budget(user_id: int, round_number: int, query_count: int) -> int:
    """Derive a candidate search budget from workspace size rather than fixed chunk quotas."""
    try:
        result = collection.get(where={"user_id": int(user_id)}, include=[])
        total = len(result.get("ids", [])) if result else 0
    except Exception:
        total = 0

    if total <= 0:
        return max(8, 6 * max(1, query_count))

    # Candidate budget is only a search safety budget. It is not a final answer chunk count.
    base = int(max(8, min(60, math.ceil(math.sqrt(total) * 4))))
    expansion = 1.0 + 0.35 * max(0, round_number - 1)
    return int(min(80, max(8, math.ceil(base * expansion))))


def _source_key(chunk: Dict[str, Any]) -> str:
    meta = chunk.get("metadata", {}) or {}
    document_id = meta.get("document_id")
    chunk_number = meta.get("chunk_number")
    page = meta.get("page_number")
    if document_id is not None and chunk_number is not None:
        return f"{document_id}:{chunk_number}"
    return f"{document_id}:{page}:{hash(chunk.get('text', ''))}"


def query_vector_store(
    search_queries: List[str],
    user_id: int,
    candidate_k: int = 20,
) -> List[Dict[str, Any]]:
    """Run semantic searches with strict user isolation and source-aware deduplication."""
    seen_sources = set()
    all_candidates = []

    for query_text in search_queries:
        if not query_text.strip():
            continue
        try:
            q_emb = model.encode(query_text)
            results = collection.query(
                query_embeddings=[q_emb.tolist()],
                n_results=int(candidate_k),
                where={"user_id": int(user_id)},
                include=["documents", "metadatas", "distances"],
            )
            docs = (results or {}).get("documents", [[]])[0]
            metas = (results or {}).get("metadatas", [[]])[0]
            dists = (results or {}).get("distances", [[]])[0]

            for i, text_content in enumerate(docs):
                metadata = metas[i] if i < len(metas) else {}
                chunk = {
                    "text": text_content,
                    "metadata": metadata or {},
                    "score": dists[i] if i < len(dists) else None,
                    "matched_query": query_text,
                }
                key = _source_key(chunk)
                if key not in seen_sources:
                    seen_sources.add(key)
                    all_candidates.append(chunk)
        except Exception as exc:
            logging.error("Vector store search failed for query '%s' (user=%s): %s", query_text, user_id, exc)

    return all_candidates


def _merge_candidates(existing: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged = list(existing)
    seen = {_source_key(c) for c in merged}
    for chunk in new:
        key = _source_key(chunk)
        if key not in seen:
            seen.add(key)
            merged.append(chunk)
    return merged


def retrieve_adaptive(
    plan: Dict[str, Any],
    user_id: int,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Iteratively retrieve, rerank, evaluate coverage, and expand missing evidence."""
    original_question = plan.get("original_question", "")
    max_rounds = int(plan.get("max_rounds", 3))
    search_queries = list(plan.get("search_queries") or [original_question])

    candidates: List[Dict[str, Any]] = []
    final_ranked: List[Dict[str, Any]] = []
    final_eval: Dict[str, Any] = {}

    for round_number in range(1, max_rounds + 1):
        budget = _candidate_budget(user_id, round_number, len(search_queries))
        round_candidates = query_vector_store(search_queries, user_id, candidate_k=budget)

        # Workspace-wide synthesis needs representative evidence from the user's
        # actual workspace. Retrieve a small adaptive slice from each indexed
        # document rather than assuming that global nearest-neighbor search will
        # surface every document.
        if plan.get("needs_workspace_coverage"):
            try:
                doc_rows = collection.get(
                    where={"user_id": int(user_id)},
                    include=["metadatas"],
                )
                doc_ids = sorted({
                    str((m or {}).get("document_id"))
                    for m in (doc_rows or {}).get("metadatas", [])
                    if (m or {}).get("document_id") is not None
                })
                if doc_ids:
                    workspace_query = search_queries[0] if search_queries else original_question
                    q_emb = model.encode(workspace_query)
                    for doc_id in doc_ids:
                        try:
                            scoped = collection.query(
                                query_embeddings=[q_emb.tolist()],
                                n_results=max(3, min(8, int(math.ceil(math.sqrt(max(1, budget)))))),
                                where={
                                    "$and": [
                                        {"user_id": int(user_id)},
                                        {"document_id": doc_id},
                                    ]
                                },
                                include=["documents", "metadatas", "distances"],
                            )
                            docs = (scoped or {}).get("documents", [[]])[0]
                            metas = (scoped or {}).get("metadatas", [[]])[0]
                            dists = (scoped or {}).get("distances", [[]])[0]
                            for i, text_content in enumerate(docs):
                                round_candidates.append({
                                    "text": text_content,
                                    "metadata": metas[i] if i < len(metas) else {},
                                    "score": dists[i] if i < len(dists) else None,
                                    "matched_query": workspace_query,
                                })
                        except Exception as doc_exc:
                            logging.warning("Workspace retrieval failed for document %s: %s", doc_id, doc_exc)
            except Exception as workspace_exc:
                logging.warning("Workspace coverage retrieval failed: %s", workspace_exc)

        candidates = _merge_candidates(candidates, round_candidates)

        ranked = rerank_chunks(
            original_question,
            candidates,
            query_variants=search_queries + [
                str(r.get("target_text", ""))
                for r in plan.get("evidence_requirements", [])
                if isinstance(r, dict) and r.get("target_text")
            ],
        )
        evaluation = evaluate_evidence_sufficiency(plan, ranked, current_round=round_number)

        docs_found = sorted({
            str((c.get("metadata", {}) or {}).get("filename", "Unknown"))
            for c in ranked
        })
        content_types = sorted({
            str((c.get("metadata", {}) or {}).get("content_type", "text"))
            for c in ranked
        })

        logging.info(
            "RAG ROUND %s | budget=%s | candidates=%s | ranked=%s | docs=%s | types=%s | evaluation=%s",
            round_number, budget, len(candidates), len(ranked), docs_found, content_types, evaluation,
        )

        final_ranked = ranked
        final_eval = evaluation

        if evaluation.get("is_sufficient"):
            break
        if round_number >= max_rounds:
            break

        expansion_queries = evaluation.get("expansion_queries") or []
        if not expansion_queries:
            break

        search_queries = list(dict.fromkeys(expansion_queries))

    logging.info(
        "RAG FINAL | chunks=%s | docs=%s | types=%s | sufficient=%s | exhausted=%s",
        len(final_ranked),
        sorted({str((c.get("metadata", {}) or {}).get("filename", "Unknown")) for c in final_ranked}),
        sorted({str((c.get("metadata", {}) or {}).get("content_type", "text")) for c in final_ranked}),
        final_eval.get("is_sufficient"),
        final_eval.get("retrieval_exhausted"),
    )

    return {
        "chunks": final_ranked,
        "plan": plan,
        "evaluation": final_eval,
        "documents": sorted({str((c.get("metadata", {}) or {}).get("filename", "Unknown")) for c in final_ranked}),
        "content_types": sorted({str((c.get("metadata", {}) or {}).get("content_type", "text")) for c in final_ranked}),
    }


def retrieve_chunks(
    query: str,
    user_id: int,
    k: int = 10,
    is_summary: bool = False,
) -> List[Dict[str, Any]]:
    """Backward-compatible entry point; retrieval behavior is still planner-driven."""
    plan = generate_retrieval_plan(query)
    # Do not override the planner with a fixed summary mode. The argument remains only
    # for API compatibility with existing callers/tests.
    result = retrieve_adaptive(plan, user_id)
    return result.get("chunks", [])
