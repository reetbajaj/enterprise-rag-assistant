import logging
import re
import os
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.services.retrieval_service import retrieve_adaptive
from app.services.query_planner import generate_retrieval_plan
from app.services.llm_service import generate_answer
from app.services.embedding_service import model
from app.database.models import Document


def is_catalog_inquiry(question: str) -> bool:
    """Checks whether the user is asking for their uploaded-document inventory."""
    q = question.lower().strip()
    patterns = [
        r"\b(?:do|did)\s+(?:i|we|you)\s+have\s+(?:any\s+)?documents?\b",
        r"\bwhat\s+documents?\s+(?:do\s+i|are)\b",
        r"\bwhat\s+files?\s+(?:do\s+i|are|have)\b",
        r"\blist\s+(?:my|the|all)?\s*(?:uploaded\s+)?(?:documents?|files?|pdfs?)\b",
        r"\bshow\s+(?:my|the|all)?\s*(?:uploaded\s+)?(?:documents?|files?|pdfs?)\b",
        r"\bwhich\s+documents?\s+(?:do\s+i|have\s+been|are)\b",
        r"\bhow\s+many\s+documents?\b",
        r"\bdo\s+you\s+see\s+(?:my\s+)?documents?\b",
    ]
    return any(re.search(pattern, q) for pattern in patterns)


def _chunk_source_key(chunk: Dict[str, Any]) -> str:
    meta = chunk.get("metadata", {}) or {}
    doc_id = meta.get("document_id")
    chunk_num = meta.get("chunk_number")
    page = meta.get("page_number")
    if doc_id is not None and chunk_num is not None:
        return f"{doc_id}:{chunk_num}"
    return f"{doc_id}:{page}:{hash(chunk.get('text', ''))}"


def _normalise_scope(value: str) -> str:
    value = str(value or "").lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\\s+", " ", value).strip()


def _scope_match(scope: str, chunk: Dict[str, Any]) -> float:
    if not scope:
        return 1.0
    meta = chunk.get("metadata", {}) or {}
    filename = _normalise_scope(meta.get("filename", ""))
    heading = _normalise_scope(meta.get("heading", ""))
    scope_norm = _normalise_scope(scope)
    if not scope_norm:
        return 1.0
    if scope_norm in filename or filename in scope_norm:
        return 1.0

    scope_words = set(scope_norm.split())
    doc_words = set((filename + " " + heading).split())
    if not scope_words:
        return 1.0
    return len(scope_words & doc_words) / len(scope_words)


def _adaptive_score_cutoff(scores: List[float]) -> float:
    """Find an evidence boundary from the observed score distribution, not a fixed k."""
    finite = sorted([float(s) for s in scores if s is not None], reverse=True)
    if not finite:
        return float("-inf")
    if len(finite) <= 2:
        return finite[-1]

    # The largest adjacent drop is the natural separation between strong and weak
    # evidence. If the distribution is flat, keep the stronger half.
    drops = [finite[i] - finite[i + 1] for i in range(len(finite) - 1)]
    idx = max(range(len(drops)), key=lambda i: drops[i])
    largest_drop = drops[idx]

    # Avoid an unstable split caused by tiny numerical noise.
    if largest_drop > max(0.35, (max(finite) - min(finite)) * 0.12):
        return finite[idx + 1]
    return finite[max(0, len(finite) // 2)]


def _select_context_chunks(
    ranked_chunks: List[Dict[str, Any]],
    plan: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Select final evidence adaptively.

    Candidate retrieval and final context are deliberately separate. Explicit
    document scope is respected when the user names a document. Workspace-wide
    requests get representative evidence from the workspace. Comparisons preserve
    evidence for each semantic target. No document names or fixed chunk quotas
    are hardcoded.
    """
    if not ranked_chunks:
        return []

    try:
        max_chars = int(os.getenv("RAG_CONTEXT_MAX_CHARS", "14000"))
    except ValueError:
        max_chars = 14000
    max_chars = max(6000, min(max_chars, 24000))

    reqs = plan.get("evidence_requirements") or []
    scopes = [
        str(r.get("document_scope") or r.get("scope") or "").strip()
        for r in reqs if isinstance(r, dict)
    ]
    explicit_scopes = [s for s in scopes if s]

    # If the query explicitly scopes to a document, eliminate candidates from
    # unrelated documents before context construction.
    pool = list(ranked_chunks)
    if explicit_scopes:
        scoped = [
            c for c in pool
            if max(_scope_match(s, c) for s in explicit_scopes) >= 0.50
        ]
        if scoped:
            pool = scoped

    # For comparisons, require target coverage where possible by matching each
    # requirement independently against candidate text.
    target_texts = [
        str(r.get("target_text") or r.get("target") or "").strip()
        for r in reqs if isinstance(r, dict)
    ]
    target_texts = [t for t in target_texts if t]

    # Use the embedding model to calculate target-specific relevance. This avoids
    # relying solely on the single original-question CrossEncoder score.
    query_texts = [str(plan.get("original_question", "")).strip()] + target_texts
    query_texts = list(dict.fromkeys(q for q in query_texts if q))
    candidate_texts = [
        " ".join([
            str((c.get("metadata", {}) or {}).get("filename", "")),
            str((c.get("metadata", {}) or {}).get("heading", "")),
            str(c.get("text", "")),
        ]).strip()
        for c in pool
    ]
    try:
        qvecs = model.encode(query_texts, normalize_embeddings=True)
        cvecs = model.encode(candidate_texts, normalize_embeddings=True)
        semantic = (cvecs @ qvecs.T).max(axis=1).tolist()
    except Exception:
        semantic = [0.0] * len(pool)

    for idx, chunk in enumerate(pool):
        chunk["_final_semantic_score"] = float(semantic[idx])
        chunk["_final_scope_score"] = max(
            [_scope_match(s, chunk) for s in explicit_scopes] or [1.0]
        )

    # Combine normalized semantic and reranker evidence. The exact scale is learned
    # from the current candidate pool, so a new workspace/document does not inherit
    # a hardcoded score threshold.
    rerank_values = [
        float(c.get("rerank_score"))
        for c in pool if c.get("rerank_score") is not None
    ]
    rmin, rmax = (min(rerank_values), max(rerank_values)) if rerank_values else (0.0, 1.0)
    rspan = max(rmax - rmin, 1e-9)
    for c in pool:
        rs = float(c.get("rerank_score", rmin))
        rn = (rs - rmin) / rspan
        sn = max(0.0, min(1.0, (c.get("_final_semantic_score", 0.0) + 1.0) / 2.0))
        c["_final_relevance"] = 0.60 * rn + 0.40 * sn

    pool.sort(key=lambda c: c.get("_final_relevance", 0.0), reverse=True)
    cutoff = _adaptive_score_cutoff([c.get("_final_relevance", 0.0) for c in pool])

    needs_multi = bool(plan.get("needs_multiple_sources", False))
    needs_workspace = bool(plan.get("needs_workspace_coverage", False))

    # For ordinary focused questions, determine which documents are genuinely
    # competitive using the observed score distribution. This prevents a broad
    # workspace candidate pool from leaking unrelated documents into the final
    # context. Multi-source/workspace requests deliberately bypass this filter.
    allowed_doc_ids = None
    if not explicit_scopes and not needs_multi and not needs_workspace:
        by_doc = {}
        for c in pool:
            did = str((c.get("metadata", {}) or {}).get("document_id", ""))
            by_doc.setdefault(did, []).append(c)

        doc_best = sorted(
            [(did, max(float(x.get("_final_relevance", 0.0)) for x in xs))
             for did, xs in by_doc.items()],
            key=lambda item: item[1],
            reverse=True,
        )
        if len(doc_best) > 1:
            doc_scores = [score for _, score in doc_best]
            doc_drops = [doc_scores[i] - doc_scores[i + 1] for i in range(len(doc_scores) - 1)]
            gap_idx = max(range(len(doc_drops)), key=lambda i: doc_drops[i])
            gap = doc_drops[gap_idx]
            spread = max(doc_scores) - min(doc_scores)
            if gap > max(0.10, spread * 0.18):
                allowed_doc_ids = {did for did, _ in doc_best[:gap_idx + 1]}
            else:
                # When document scores overlap, retain only documents whose best
                # evidence is at least the median of the observed document scores.
                # This is distribution-based rather than a fixed document quota.
                median_doc = doc_scores[len(doc_scores) // 2] if doc_scores else 0.0
                allowed_doc_ids = {did for did, score in doc_best if score >= median_doc}

        if allowed_doc_ids:
            pool = [
                c for c in pool
                if str((c.get("metadata", {}) or {}).get("document_id", "")) in allowed_doc_ids
            ]

    selected = []
    used = set()
    used_chars = 0

    def add_candidate(c):
        nonlocal used_chars
        key = _chunk_source_key(c)
        if key in used:
            return False
        text = str(c.get("text", "")).strip()
        if not text:
            return False
        cost = len(text)
        if selected and used_chars + cost > max_chars:
            return False
        selected.append(c)
        used.add(key)
        used_chars += cost
        return True

    if needs_multi and len(target_texts) >= 2:
        # For each target, add the strongest evidence that actually matches that target.
        # A document is included because its evidence matches a target, never because
        # of a fixed per-document quota.
        for target in target_texts:
            try:
                tv = model.encode([target], normalize_embeddings=True)[0]
                cv = model.encode(candidate_texts, normalize_embeddings=True)
                target_scores = (cv @ tv).tolist()
            except Exception:
                target_scores = [0.0] * len(pool)

            order = sorted(range(len(pool)), key=lambda i: target_scores[i], reverse=True)
            for i in order:
                c = pool[i]
                if target_scores[i] < 0.30 and selected:
                    break
                if add_candidate(c):
                    break

        # Fill only with evidence that remains inside the adaptive boundary.
        for c in pool:
            if c.get("_final_relevance", 0.0) >= cutoff:
                add_candidate(c)

    elif needs_workspace:
        # Broad workspace synthesis: preserve representative evidence from every
        # document that has meaningful candidates, while respecting the context budget.
        by_doc = {}
        for c in pool:
            did = str((c.get("metadata", {}) or {}).get("document_id", ""))
            by_doc.setdefault(did, []).append(c)

        for doc_chunks in sorted(
            by_doc.values(),
            key=lambda xs: max(x.get("_final_relevance", 0.0) for x in xs),
            reverse=True,
        ):
            best = max(doc_chunks, key=lambda x: x.get("_final_relevance", 0.0))
            if best.get("_final_relevance", 0.0) >= cutoff or len(by_doc) <= 2:
                add_candidate(best)

        for c in pool:
            if c.get("_final_relevance", 0.0) >= cutoff:
                add_candidate(c)

    else:
        for c in pool:
            if c.get("_final_relevance", 0.0) >= cutoff:
                add_candidate(c)

    # Always retain at least the strongest evidence if the adaptive split was too
    # aggressive, but never flood the LLM with the full candidate pool.
    if not selected and pool:
        add_candidate(pool[0])

    selected.sort(key=lambda c: c.get("_final_relevance", 0.0), reverse=True)

    # Internal fields are telemetry only and should never leak to the API.
    for c in selected:
        c.pop("_final_semantic_score", None)
        c.pop("_final_scope_score", None)
        c.pop("_final_relevance", None)

    return selected


def answer_question(
    question: str,
    user_id: int,
    db: Optional[Session] = None,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Run adaptive retrieval, evidence verification, grounded generation, and citations."""
    logging.info("RAG: processing question for user=%s: %r", user_id, question)

    if is_catalog_inquiry(question) and db is not None:
        user_docs = (
            db.query(Document)
            .filter(Document.user_id == user_id, Document.status == "completed")
            .order_by(Document.uploaded_at.desc())
            .all()
        )
        if not user_docs:
            return {
                "answer": "You haven't uploaded any documents yet. Upload a PDF in the **Documents** section to start asking questions about your files.",
                "sources": [],
                "retrieved_chunks": [],
            }

        doc_lines = [
            f"- **{doc.filename}** ({doc.chunks} vector passages, indexed on {doc.uploaded_at.strftime('%b %d, %Y')})"
            for doc in user_docs
        ]
        return {
            "answer": f"You have **{len(user_docs)}** document(s) uploaded and ready in your workspace:\n\n" +
                      "\n".join(doc_lines) +
                      "\n\nYou can ask specific questions about any of these documents or ask me to summarize them.",
            "sources": [],
            "retrieved_chunks": [],
        }

    plan = generate_retrieval_plan(question, conversation_history=conversation_history)
    retrieval_result = retrieve_adaptive(plan, user_id, conversation_history=conversation_history)
    candidate_chunks = retrieval_result.get("chunks", [])
    evaluation = retrieval_result.get("evaluation", {})

    # If zero evidence was retrieved across all rounds
    if not candidate_chunks:
        return {
            "answer": "I couldn't find information about that in your uploaded documents.",
            "sources": [],
            "retrieved_chunks": [],
        }

    # Final Context Selection (strictly separated from candidate pool)
    final_context_chunks = _select_context_chunks(candidate_chunks, plan)
    if not final_context_chunks:
        return {
            "answer": "I couldn't find information about that in your uploaded documents.",
            "sources": [],
            "retrieved_chunks": [],
        }

    # Telemetry logging separating candidates from selected final context
    candidate_docs = sorted({str((c.get("metadata", {}) or {}).get("filename", "Unknown")) for c in candidate_chunks})
    final_docs = sorted({str((c.get("metadata", {}) or {}).get("filename", "Unknown")) for c in final_context_chunks})
    final_types = sorted({str((c.get("metadata", {}) or {}).get("content_type", "text")) for c in final_context_chunks})

    logging.info(
        "\n=======================================================\n"
        "QUERY: %s\n"
        "RETRIEVAL CANDIDATES: %s (Docs: %s)\n"
        "EVIDENCE REQUIREMENTS: %s\n"
        "SELECTED FINAL CONTEXT: %s chunks (Docs: %s | Types: %s)\n"
        "=======================================================",
        question,
        len(candidate_chunks),
        candidate_docs,
        plan.get("evidence_requirements"),
        len(final_context_chunks),
        final_docs,
        final_types,
    )

    context_blocks = []
    for chunk in final_context_chunks:
        meta = chunk.get("metadata", {}) or {}
        fn = meta.get("filename", "Document")
        pg = meta.get("page_number", 1)
        ctype = meta.get("content_type", "text")
        heading = meta.get("heading", "")
        tags = [f"Document: {fn}", f"Page: {pg}", f"Type: {str(ctype).capitalize()}"]
        if heading:
            tags.append(f"Heading: {heading}")
        context_blocks.append(f"[{', '.join(tags)}]\n{chunk['text']}")

    context = "\n\n---\n\n".join(context_blocks)
    
    # Grounded answer generation using only selected final context
    answer = generate_answer(question, context)

    # Citations generated STRICTLY from final_context_chunks
    sources = []
    for chunk in final_context_chunks:
        meta = chunk.get("metadata", {}) or {}
        sources.append({
            "filename": meta.get("filename", "Unknown Document"),
            "page_number": meta.get("page_number", 1),
            "chunk_number": meta.get("chunk_number", 0),
            "chunk_type": meta.get("chunk_type", "text"),
            "content_type": meta.get("content_type", meta.get("chunk_type", "text")),
            "source_type": meta.get("source_type", "pdf_text"),
            "heading": meta.get("heading", ""),
            "rerank_score": round(chunk.get("rerank_score"), 3) if chunk.get("rerank_score") is not None else None,
            "snippet": chunk.get("text", "")[:280] + ("..." if len(chunk.get("text", "")) > 280 else ""),
        })

    logging.info(
        "FINAL SOURCES (%s): %s",
        len(sources),
        [(s["filename"], s["page_number"], s["content_type"], s["rerank_score"]) for s in sources]
    )

    return {
        "answer": answer,
        "sources": sources,
        "retrieved_chunks": final_context_chunks,
    }
