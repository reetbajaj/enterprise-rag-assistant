import logging
import re
from typing import Dict, Any, List, Optional, Union

import numpy as np

from app.services.embedding_service import model


def normalize_evidence_requirement(raw: Any) -> Dict[str, Any]:
    """
    Normalizes arbitrary requirement representations (string, dict, nested dict, list)
    into a clean structured format separating semantic target text from coverage metadata.
    Never returns raw JSON/dictionary syntax inside target_text.
    """
    if isinstance(raw, dict):
        # Extract target text from common keys
        target = (
            raw.get("target")
            or raw.get("target_text")
            or raw.get("concept")
            or raw.get("topic")
            or raw.get("requirement")
            or raw.get("entity")
            or ""
        )
        # If target itself is a dict, recurse
        if isinstance(target, dict):
            return normalize_evidence_requirement(target)

        target_text = str(target).strip()
        scope = str(raw.get("scope", "")).strip()
        doc_scope = str(raw.get("document_scope", raw.get("document", ""))).strip()
        required = bool(raw.get("required", True))

        # If target_text was empty but scope has info, use scope
        if not target_text and scope:
            target_text = scope

        # Clean meta-language from target_text
        target_text = _clean_meta_instructions(target_text)

        return {
            "target_text": target_text or "general information",
            "scope": scope,
            "document_scope": doc_scope,
            "required": required,
            "raw": raw,
        }

    if isinstance(raw, (list, tuple)):
        parts = [str(normalize_evidence_requirement(x)["target_text"]) for x in raw if x]
        combined = " ".join(parts).strip()
        return {
            "target_text": _clean_meta_instructions(combined) or "general information",
            "scope": "",
            "document_scope": "",
            "required": True,
            "raw": raw,
        }

    # If it is a string or primitive
    text = str(raw).strip()
    # Check if text looks like a stringified Python dict or JSON
    if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
        try:
            import ast
            parsed = ast.literal_eval(text)
            if isinstance(parsed, (dict, list)):
                return normalize_evidence_requirement(parsed)
        except Exception:
            pass

    cleaned = _clean_meta_instructions(text)
    return {
        "target_text": cleaned if cleaned else "general overview main concepts",
        "scope": "",
        "document_scope": "",
        "required": True,
        "raw": raw,
    }


def _clean_meta_instructions(text: str) -> str:
    """Removes procedural instruction phrases to leave pure semantic concepts."""
    t = str(text).strip()
    # Remove procedural instruction prefixes
    t = re.sub(
        r"^(?:extract|identify|find|summarize|list|retrieve|explain|provide)\s+(?:\d+\s+)?(?:main|key|important|concise)?\s*(?:points|concepts|information|themes|topics|details|summaries)?\s*(?:from|in|across|about|of)?\s*(?:the\s+document(?:s)?|all\s+documents?|each\s+document|the\s+content)?[\s,;:-]*",
        "",
        t,
        flags=re.IGNORECASE
    ).strip()
    # Remove trailing constraint clauses
    t = re.sub(
        r"\b(?:without\s+specifying\s+what\s+they\s+are|in\s+\d+\s+bullet\s+points.*|or\s+similar\s+format|in\s+bullet\s+points.*|concise\s+summaries\s+of\s+the\s+document.*)\b",
        "",
        t,
        flags=re.IGNORECASE
    ).strip()
    return t.strip(" :,-;.")


def _candidate_text(chunk: Dict[str, Any]) -> str:
    meta = chunk.get("metadata", {}) or {}
    return " ".join([
        str(chunk.get("text", "")),
        str(meta.get("filename", "")),
        str(meta.get("heading", "")),
    ]).strip()


def _semantic_coverage(target_text: str, candidates: List[Dict[str, Any]]) -> float:
    """Computes semantic similarity between normalized target text and candidate chunks."""
    if not target_text or not candidates:
        return 0.0

    texts = [_candidate_text(c) for c in candidates[:40] if _candidate_text(c)]
    if not texts:
        return 0.0

    try:
        req_vec = model.encode([target_text], normalize_embeddings=True)[0]
        text_vecs = model.encode(texts, normalize_embeddings=True)
        scores = np.dot(text_vecs, req_vec)
        best_semantic = float(np.max(scores))
    except Exception as exc:
        logging.warning("Semantic embedding coverage fallback: %s", exc)
        best_semantic = 0.0

    # Supporting keyword overlap signal
    words = set(re.findall(r"\w{3,}", target_text.lower()))
    best_overlap = 0.0
    if words:
        for text in texts:
            text_words = set(re.findall(r"\w{3,}", text.lower()))
            overlap = len(words & text_words) / len(words)
            if overlap > best_overlap:
                best_overlap = overlap

    # Weighted blend giving primary weight to semantic similarity with keyword boost
    combined_score = max(best_semantic, best_overlap * 0.7 + best_semantic * 0.3)
    return float(combined_score)


def _document_ids(candidates: List[Dict[str, Any]]) -> set:
    return {
        str((c.get("metadata", {}) or {}).get("document_id"))
        for c in candidates
        if (c.get("metadata", {}) or {}).get("document_id") is not None
    }


def _requirement_document_scope(req: Dict[str, Any]) -> str:
    return str(
        req.get("document_scope")
        or req.get("scope")
        or ""
    ).strip()


def _scope_coverage(scope: str, candidates: List[Dict[str, Any]]) -> float:
    """Measure whether candidate metadata/text represents an explicitly requested scope."""
    if not scope:
        return 1.0
    scope_words = set(re.findall(r"\w{3,}", scope.lower()))
    if not scope_words:
        return 1.0

    best = 0.0
    for chunk in candidates:
        meta = chunk.get("metadata", {}) or {}
        haystack = " ".join([
            str(meta.get("filename", "")),
            str(meta.get("heading", "")),
            str(chunk.get("text", "")),
        ]).lower()
        words = set(re.findall(r"\w{3,}", haystack))
        if scope_words:
            best = max(best, len(scope_words & words) / len(scope_words))
    return best


def evaluate_evidence_sufficiency(
    plan: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    current_round: int = 1,
) -> Dict[str, Any]:
    """
    Evaluate semantic target coverage, explicit document scope, visual evidence,
    and workspace breadth without static document/page quotas.
    """
    max_rounds = int(plan.get("max_rounds", 3))
    raw_requirements = list(plan.get("evidence_requirements") or [])
    needs_multiple_sources = bool(plan.get("needs_multiple_sources", False))
    needs_visual = bool(plan.get("needs_visual_evidence", False))
    needs_workspace = bool(plan.get("needs_workspace_coverage", False))

    normalized_reqs = [normalize_evidence_requirement(r) for r in raw_requirements]

    if not candidates:
        missing = [r["target_text"] for r in normalized_reqs if r.get("target_text")]
        return {
            "is_sufficient": False,
            "retrieval_exhausted": current_round >= max_rounds,
            "missing_requirements": missing or [plan.get("original_question", "")],
            "missing_targets": missing or [plan.get("original_question", "")],
            "coverage": {},
            "reason": "No candidate evidence was retrieved",
            "expansion_queries": list(plan.get("search_queries", []))[:5],
            "document_count": 0,
            "content_types": [],
        }

    missing_targets = []
    coverage_scores = {}
    scoped_document_sets = []

    for req in normalized_reqs:
        target = req.get("target_text", "").strip()
        if not target:
            continue

        semantic = _semantic_coverage(target, candidates)
        scope = _requirement_document_scope(req)
        scope_score = _scope_coverage(scope, candidates) if scope else 1.0

        # Keep semantic target and scope separate. A strong semantic match in the
        # wrong document is not sufficient when the user explicitly named a document.
        combined = semantic if not scope else min(semantic, max(scope_score, 0.0))
        coverage_scores[target] = round(combined, 4)

        if semantic < 0.30:
            missing_targets.append(target)
        elif scope and scope_score < 0.50:
            missing_targets.append(f"{target} in {scope}")

        if scope:
            matching_docs = {
                str((c.get("metadata", {}) or {}).get("document_id"))
                for c in candidates
                if scope.lower() in str((c.get("metadata", {}) or {}).get("filename", "")).lower()
            }
            if matching_docs:
                scoped_document_sets.append(matching_docs)

    document_ids = _document_ids(candidates)
    content_types = {
        str((c.get("metadata", {}) or {}).get("content_type", "text"))
        for c in candidates
    }

    if needs_multiple_sources and len(document_ids) < 2:
        missing_targets.append("Evidence from all required source targets")

    if needs_visual and not content_types.intersection({"table", "diagram", "figure", "chart", "ocr"}):
        missing_targets.append("Relevant visual, table, chart, diagram, or OCR evidence")

    # Workspace breadth is evaluated by document diversity, not a fixed chunk/page minimum.
    # If there are candidates from the workspace, don't reject a short but valid workspace.
    if needs_workspace and len(document_ids) == 0:
        missing_targets.append("Workspace evidence")

    is_sufficient = len(missing_targets) == 0
    retrieval_exhausted = current_round >= max_rounds

    expansion_queries = []
    if missing_targets and not retrieval_exhausted:
        for target in missing_targets[:4]:
            expansion_queries.append(str(target))
        expansion_queries.extend(plan.get("search_queries", []))
        expansion_queries = list(dict.fromkeys(
            q.strip() for q in expansion_queries if str(q).strip()
        ))[:6]

    result = {
        "is_sufficient": is_sufficient,
        "retrieval_exhausted": retrieval_exhausted,
        "missing_requirements": missing_targets,
        "missing_targets": missing_targets,
        "coverage": coverage_scores,
        "document_count": len(document_ids),
        "content_types": sorted(content_types),
        "reason": "Evidence covers the retrieval requirements" if is_sufficient else "Evidence coverage is incomplete",
        "expansion_queries": expansion_queries,
    }
    logging.info("Evidence evaluation: %s", result)
    return result
