import json
import logging
import re
from typing import Dict, Any, List, Optional

import requests

from app.services.evidence_evaluator import normalize_evidence_requirement

OLLAMA_URL = "http://localhost:11434/api/generate"
PLANNER_MODEL = "llama3.2"


def _conversation_text(conversation_history: Optional[List[Dict[str, Any]]]) -> str:
    if not conversation_history:
        return ""
    recent = conversation_history[-6:]
    lines = []
    for item in recent:
        role = item.get("role", "user")
        content = str(item.get("content", item.get("message", ""))).strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _table_query_variants(question: str) -> List[str]:
    """
    Generate document-agnostic lexical variants for structured-table questions.
    This is field vocabulary expansion, not document/company hardcoding.
    """
    q = question.strip()
    lower = q.lower()
    if not re.search(
        r"\b(?:table|price|close|closing|current|sema|trend|pivot|support|resistance|"
        r"change|open|high|low|volume|stock|company)\b",
        lower,
    ):
        return []

    variants = []
    replacements = [
        (r"\bclosing\s+price\b", "Close"),
        (r"\bclosing\s+value\b", "Close"),
        (r"\bcurrent\s+price\b", "Close"),
        (r"\bcurrent\s+value\b", "Close"),
        (r"\bprevious\s+close\b", "Close"),
        (r"\b20\s*day\s*simple\s*moving\s*average\b", "20 SEMA"),
        (r"\bshort[-\s]?term\s+equity\s+market\s+average\b", "20 SEMA"),
        (r"\buptrend\b", "UP"),
        (r"\bdowntrend\b", "DN"),
    ]

    expanded = q
    changed = False
    for pattern, replacement in replacements:
        expanded2 = re.sub(pattern, replacement, expanded, flags=re.IGNORECASE)
        if expanded2 != expanded:
            changed = True
            expanded = expanded2

    if changed and expanded.lower() != q.lower():
        variants.append(expanded)

    # Add a compact entity + field formulation. This remains generic: the entity
    # and field words come from the user's question.
    entity_match = re.search(
        r"\b(?:of|for|about)\s+([A-Za-z][A-Za-z0-9&().'\- ]{1,80}?)(?:\s+in\b|\s*$|\?)",
        q,
        re.IGNORECASE,
    )
    if entity_match:
        entity = entity_match.group(1).strip(" ?.")
        field_terms = []
        if re.search(r"\b(?:close|closing|current|price)\b", lower):
            field_terms.append("Close")
        if re.search(r"\b20\s*sema\b|\baverage\b", lower):
            field_terms.append("20 SEMA")
        if "trend" in lower:
            field_terms.append("Trend")
        if "pivot" in lower:
            field_terms.append("Pivot")
        if field_terms:
            variants.append(f"{entity} " + " ".join(field_terms))

    return list(dict.fromkeys(v for v in variants if v.strip()))[:3]


def _extract_comparison_targets(question: str) -> List[str]:
    q = question.strip()
    patterns = [
        r"\b(?:compare|contrast)\s+(.+?)\s+(?:and|with|versus|vs\.?)\s+(.+)$",
        r"\b(?:differences?|similarities?)\s+between\s+(.+?)\s+and\s+(.+)$",
        r"\bbetween\s+(.+?)\s+and\s+(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, q, re.IGNORECASE)
        if match:
            targets = []
            for group in match.groups():
                value = re.sub(r"[?.!]$", "", group).strip()
                value = re.sub(r"\b(?:the|these|those|both|uploaded|documents?)\b", "", value, flags=re.I).strip()
                if value:
                    targets.append(value)
            if len(targets) >= 2:
                return targets[:4]
    return []


def _fallback_plan(question: str, conversation_history: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    q = question.strip()
    targets = _extract_comparison_targets(q)
    lower = q.lower()

    broad_signals = bool(re.search(
        r"\b(?:summar\w*|overview\w*|important|key|main|entire|overall|all|across|comprehensive|takeaways)\b",
        lower,
    ))
    visual_signals = bool(re.search(
        r"\b(?:table|diagram|figure|chart|graph|image|screenshot|architecture|flowchart|scanned|ocr)\b",
        lower,
    ))
    multi_source = len(targets) >= 2 or bool(re.search(
        r"\b(?:both|multiple|across|between|among)\b", lower
    ))

    # Explicit document references are treated as scope hints, never as hardcoded names.
    scope_match = re.search(
        r"\b(?:in|from|of|about|for)\s+(?:the\s+)?([\w][\w .()&'_-]{1,100}?)\s+document\b",
        q,
        re.IGNORECASE,
    )
    if not scope_match:
        scope_match = re.search(
            r"\b(?:the|this|that)\s+([\w][\w .()&'_-]{1,100}?)\s+document\b",
            q,
            re.IGNORECASE,
        )
    document_scope = scope_match.group(1).strip() if scope_match else ""

    queries = [q]
    queries.extend(_table_query_variants(q))
    requirements = []
    if targets:
        for target in targets:
            requirements.append({"target": target, "scope": target, "required": True})
            queries.append(f"{target} details evidence")
    elif broad_signals:
        target = "main concepts key themes important findings"
        requirements.append({
            "target": target,
            "document_scope": document_scope,
            "required": True,
        })
        queries.append("main concepts key themes important findings")
    else:
        requirements.append({
            "target": q,
            "document_scope": document_scope,
            "required": True,
        })

    return {
        "original_question": q,
        "search_queries": list(dict.fromkeys(queries))[:6],
        "evidence_requirements": requirements,
        "needs_broad_coverage": broad_signals,
        "needs_multiple_sources": multi_source,
        "needs_visual_evidence": visual_signals,
        "needs_workspace_coverage": broad_signals and not document_scope,
        "max_rounds": 3,
    }


def _normalise_plan(raw: Dict[str, Any], question: str) -> Dict[str, Any]:
    q = question.strip()
    queries = raw.get("search_queries") or []
    if isinstance(queries, str):
        queries = [queries]
    queries = [str(x).strip() for x in queries if str(x).strip()]
    if q not in queries:
        queries.insert(0, q)

    raw_reqs = raw.get("evidence_requirements") or []
    if isinstance(raw_reqs, str):
        raw_reqs = [raw_reqs]

    normalized_reqs = [normalize_evidence_requirement(r) for r in raw_reqs if r]
    if not normalized_reqs:
        normalized_reqs = [normalize_evidence_requirement(q)]

    # Add generic structured-table query variants even when the planner LLM
    # returns only the original question.
    queries.extend(_table_query_variants(q))

    visual_hint = bool(raw.get("needs_visual_evidence", False)) or bool(
        re.search(r"\b(?:diagram|architecture|table|figure|chart|graph|flowchart|wireframe|scanned|image)\b", q.lower())
    )

    workspace_hint = bool(raw.get("needs_workspace_coverage", False))
    if not workspace_hint and bool(raw.get("needs_broad_coverage", False)):
        workspace_hint = not any(r.get("document_scope") for r in normalized_reqs)

    # Cross-document synthesis with a single semantic target needs representative
    # workspace coverage; explicit two-sided comparisons remain target-driven.
    if (
        not workspace_hint
        and bool(raw.get("needs_multiple_sources", False))
        and len(normalized_reqs) <= 1
        and not any(r.get("document_scope") for r in normalized_reqs)
        and re.search(r"\b(?:across|all|both|uploaded|documents?)\b", q, re.IGNORECASE)
    ):
        workspace_hint = True

    return {
        "original_question": q,
        "search_queries": list(dict.fromkeys(queries))[:6],
        "evidence_requirements": normalized_reqs[:8],
        "needs_broad_coverage": bool(raw.get("needs_broad_coverage", False)),
        "needs_multiple_sources": bool(raw.get("needs_multiple_sources", False)),
        "needs_visual_evidence": visual_hint,
        "needs_workspace_coverage": workspace_hint,
        "max_rounds": max(1, min(int(raw.get("max_rounds", 3)), 4)),
    }


def generate_retrieval_plan(
    question: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    q = question.strip()
    if not q:
        return _fallback_plan(question, conversation_history)

    history = _conversation_text(conversation_history)
    prompt = f"""You are a retrieval planner for a document-grounded RAG system.

Analyze the user's question and produce a retrieval plan. Uploaded documents are unknown.
Never invent document names or facts.

Return ONLY valid JSON:
{{
  "search_queries": ["..."],
  "evidence_requirements": [
    {{"target": "...", "scope": "...", "document_scope": "...", "required": true}}
  ],
  "needs_broad_coverage": false,
  "needs_multiple_sources": false,
  "needs_visual_evidence": false,
  "needs_workspace_coverage": false,
  "max_rounds": 3
}}

Rules:
- Keep the exact user question as the first search query.
- Generate additional natural-language formulations only when they improve recall.
- For comparisons, create a requirement for each target and preserve the subject being compared.
- If the user explicitly names/references a document, preserve that phrase in document_scope.
- If the user asks for a summary of a named document, scope the evidence to that document.
- Set needs_workspace_coverage true only when the user asks for a synthesis/overview across the uploaded workspace rather than one named document.
- Set needs_multiple_sources true when the answer genuinely requires evidence from multiple distinct sources.
- Set needs_visual_evidence true for table/diagram/chart/figure/scanned/OCR questions.
- Do not create fixed question categories or fixed chunk counts.

Conversation context:
{history or '[none]'}

User question:
{q}
"""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": PLANNER_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0},
            },
            timeout=12,
        )
        response.raise_for_status()
        parsed = json.loads(response.json().get("response", ""))
        plan = _normalise_plan(parsed, q)
    except Exception as exc:
        logging.warning("Adaptive query planner fallback: %s", exc)
        plan = _fallback_plan(q, conversation_history)

    logging.info("Retrieval plan: %s", plan)
    return plan
