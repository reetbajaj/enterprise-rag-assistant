import pytest
import os
import io
import fitz
from PIL import Image, ImageDraw

from app.services.query_planner import generate_retrieval_plan
from app.services.evidence_evaluator import evaluate_evidence_sufficiency, normalize_evidence_requirement
from app.services.multimodal_service import format_table_as_markdown
from app.services.vector_store import store_embeddings, delete_document
from app.services.embedding_service import generate_embeddings
from app.services.rag_service import answer_question
from app.database.database import SessionLocal


def test_requirement_normalization():
    # String requirement
    norm1 = normalize_evidence_requirement("role of data in CivicConnect")
    assert norm1["target_text"] == "role of data in CivicConnect"

    # Dictionary requirement
    norm2 = normalize_evidence_requirement({
        "target": "role of data in CivicConnect",
        "scope": "CivicConnect",
        "qualifiers": ["concept", "function"],
        "relationships": ["with other components"]
    })
    assert norm2["target_text"] == "role of data in CivicConnect"
    assert norm2["scope"] == "CivicConnect"

    # Meta-instruction requirement cleaning
    norm3 = normalize_evidence_requirement("extract 5 main points from the document, without specifying what they are")
    assert "extract 5 main points" not in norm3["target_text"]


def test_query_planner_dynamic():
    # 1. Factual Query
    plan_fact = generate_retrieval_plan("What is proof-based verification?")
    assert len(plan_fact["search_queries"]) >= 1
    assert len(plan_fact["evidence_requirements"]) >= 1

    # 2. Comparative Query
    plan_comp = generate_retrieval_plan("Compare the role of data in System Alpha and System Beta.")
    assert plan_comp["needs_multiple_sources"] is True
    assert len(plan_comp["search_queries"]) >= 2
    assert len(plan_comp["evidence_requirements"]) >= 2

    # 3. Broad Overview Query
    plan_broad = generate_retrieval_plan("Summarize the key information across all uploaded documents.")
    assert plan_broad["needs_broad_coverage"] is True

    # 4. Visual Diagram Query
    plan_visual = generate_retrieval_plan("Explain the system architecture diagram and component connections.")
    assert plan_visual["needs_visual_evidence"] is True


def test_evidence_sufficiency_evaluation():
    plan_comp = {
        "original_question": "Compare System Alpha and System Beta.",
        "evidence_requirements": [
            {"target": "System Alpha architecture features", "scope": "System Alpha"},
            {"target": "System Beta event queue specifications", "scope": "System Beta"}
        ],
        "needs_multiple_sources": True,
        "needs_visual_evidence": False,
        "max_rounds": 2
    }

    # Only Alpha is retrieved -> Insufficient
    candidates_alpha_only = [
        {"text": "System Alpha architecture features include microservices and REST API.", "metadata": {"filename": "alpha.pdf", "document_id": "doc_alpha", "content_type": "text"}, "rerank_score": 3.5}
    ]
    eval_1 = evaluate_evidence_sufficiency(plan_comp, candidates_alpha_only, current_round=1)
    assert eval_1["is_sufficient"] is False
    assert len(eval_1["missing_targets"]) > 0
    assert len(eval_1["expansion_queries"]) > 0

    # Both Alpha and Beta are retrieved -> Sufficient
    candidates_both = [
        {"text": "System Alpha architecture features include microservices and REST API.", "metadata": {"filename": "alpha.pdf", "document_id": "doc_alpha", "content_type": "text"}, "rerank_score": 3.5},
        {"text": "System Beta event queue specifications relies on event-driven message brokers.", "metadata": {"filename": "beta.pdf", "document_id": "doc_beta", "content_type": "text"}, "rerank_score": 2.8}
    ]
    eval_2 = evaluate_evidence_sufficiency(plan_comp, candidates_both, current_round=1)
    assert eval_2["is_sufficient"] is True
    assert len(eval_2["missing_targets"]) == 0


def test_end_to_end_adaptive_rag_synthetic_multimodal():
    """
    Creates synthetic documents for User 8888:
    - doc1: Cloud Native Database (table comparing Read/Write latency)
    - doc2: Distributed Messaging (architecture diagram & overview)
    Tests comparative query, table query, and diagram query end-to-end.
    """
    user_id = 8888
    doc1_id = "doc_cloud_db_8888"
    doc2_id = "doc_messaging_8888"

    doc1_chunks = [
        {
            "text": "Cloud Native Database Overview: High availability storage engine with automatic sharding.",
            "page_number": 1,
            "chunk_type": "text",
            "content_type": "text",
            "source_type": "pdf_text",
            "heading": "Database Overview",
            "has_images": False
        },
        {
            "text": "### Latency Performance Table\n\n| Engine | Read Latency | Write Latency |\n|---|---|---|\n| CloudDB Alpha | 5ms | 10ms |\n| LegacySQL | 45ms | 80ms |",
            "page_number": 2,
            "chunk_type": "table",
            "content_type": "table",
            "source_type": "pdf_table",
            "heading": "Latency Performance Table",
            "has_images": False
        }
    ]

    doc2_chunks = [
        {
            "text": "Distributed Messaging System: Event streaming backbone designed for decoupled services.",
            "page_number": 1,
            "chunk_type": "text",
            "content_type": "text",
            "source_type": "pdf_text",
            "heading": "Messaging Overview",
            "has_images": False
        },
        {
            "text": "### Figure 1: Event Broker Architecture\n**Visual Type**: Diagram\n**Labels & Extracted Components**: Producer App -> Kafka Broker -> Consumer Workers -> Analytics Engine",
            "page_number": 2,
            "chunk_type": "diagram",
            "content_type": "diagram",
            "source_type": "pdf_visual",
            "heading": "Event Broker Architecture",
            "has_images": True
        }
    ]

    embs1 = generate_embeddings([c["text"] for c in doc1_chunks])
    store_embeddings(doc1_id, "CloudDB_Spec.pdf", doc1_chunks, embs1, user_id)

    embs2 = generate_embeddings([c["text"] for c in doc2_chunks])
    store_embeddings(doc2_id, "Distributed_Messaging.pdf", doc2_chunks, embs2, user_id)

    db = SessionLocal()
    try:
        # 1. Comparative Query across both documents
        res_comp = answer_question("Compare Cloud Native Database and Distributed Messaging System.", user_id, db=db)
        assert len(res_comp["sources"]) >= 2
        source_files = set(s["filename"] for s in res_comp["sources"])
        assert "CloudDB_Spec.pdf" in source_files
        assert "Distributed_Messaging.pdf" in source_files

        # 2. Table Query
        res_tab = answer_question("What is the read latency of CloudDB Alpha?", user_id, db=db)
        assert "5ms" in res_tab["answer"] or "5" in res_tab["answer"]
        assert any(s["content_type"] == "table" for s in res_tab["sources"])

        # 3. Diagram Query
        res_diag = answer_question("What components are shown in the Event Broker Architecture diagram?", user_id, db=db)
        assert "Kafka" in res_diag["answer"] or "Producer" in res_diag["answer"] or "Broker" in res_diag["answer"]
        assert any(s["content_type"] == "diagram" for s in res_diag["sources"])

    finally:
        delete_document(doc1_id, user_id)
        delete_document(doc2_id, user_id)
        db.close()
