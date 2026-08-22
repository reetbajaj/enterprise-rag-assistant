import re
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.services.retrieval_service import retrieve_chunks
from app.services.llm_service import generate_answer
from app.services.query_rewriter import rewrite_query
from app.database.models import Document


def is_catalog_inquiry(question: str) -> bool:
    """Checks if the user is asking about their uploaded files/documents inventory."""
    q = question.lower().strip()
    patterns = [
        r"\b(do|did)\s+(i|we|you)\s+have\s+(any\s+)?documents?\b",
        r"\bwhat\s+documents?\s+(do\s+i|are)\b",
        r"\bwhat\s+files?\s+(do\s+i|are|have)\b",
        r"\blist\s+(my|the|all)?\s*(uploaded\s+)?(documents?|files?|pdfs?)\b",
        r"\bshow\s+(my|the|all)?\s*(uploaded\s+)?(documents?|files?|pdfs?)\b",
        r"\bwhich\s+documents?\s+(do\s+i|have\s+been|are)\b",
        r"\bhow\s+many\s+documents?\b",
        r"\bdo\s+you\s+see\s+(my\s+)?documents?\b",
    ]
    for pattern in patterns:
        if re.search(pattern, q):
            return True
    return False


def is_general_summary_inquiry(question: str) -> bool:
    """Checks if the user is asking for a general multi-document summary across all files."""
    q = question.lower().strip()
    has_summary_word = bool(re.search(r"\b(summar(y|ize|ise)|overview|key\s+(information|points|takeaways)|main\s+topics)\b", q))
    has_general_target = bool(re.search(r"\b(my|the|all|both)\s+(uploaded\s+)?documents?\b", q)) or q in ["summarize", "overview", "give me a summary"]
    # If the user targets a specific document name (e.g. "IoT document"), it's not a generic all-doc summary
    has_specific_name = bool(re.search(r"\b(iot|civicconnect|safeentry|policy|handbook)\b", q))
    return has_summary_word and has_general_target and not has_specific_name


def answer_question(
    question: str,
    user_id: int,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    logging.info(f"RAG: processing question for user={user_id}: '{question}'")

    # 1. Check if user is asking about uploaded document inventory / catalog
    if is_catalog_inquiry(question) and db is not None:
        user_docs = (
            db.query(Document)
            .filter(
                Document.user_id == user_id,
                Document.status == "completed"
            )
            .order_by(Document.uploaded_at.desc())
            .all()
        )

        if not user_docs:
            return {
                "answer": "You haven't uploaded any documents yet. Upload a PDF in the **Documents** section to start asking questions about your files.",
                "sources": [],
                "retrieved_chunks": []
            }

        doc_lines = [
            f"- **{doc.filename}** ({doc.chunks} vector passages, indexed on {doc.uploaded_at.strftime('%b %d, %Y')})"
            for doc in user_docs
        ]
        doc_list_formatted = "\n".join(doc_lines)
        return {
            "answer": f"You have **{len(user_docs)}** document(s) uploaded and ready in your workspace:\n\n{doc_list_formatted}\n\nYou can ask specific questions about any of these documents or ask me to summarize them.",
            "sources": [],
            "retrieved_chunks": []
        }

    # 2. Check if this is a general workspace summary request
    is_general_summary = is_general_summary_inquiry(question)

    if is_general_summary:
        logging.info(f"RAG: detected general summary intent for user={user_id}")
        search_query = "executive summary overview key points main topics document content"
        chunks = retrieve_chunks(
            search_query,
            user_id,
            k=10,
            is_summary=True
        )
    else:
        # 3. Specific QA or comparative query: rewrite query for semantic search
        rewritten_question = rewrite_query(question)
        logging.info(f"RAG: rewritten query: '{rewritten_question}'")

        chunks = retrieve_chunks(
            rewritten_question,
            user_id,
            k=10,
            is_summary=False
        )

    logging.info(f"RAG: {len(chunks)} chunks selected after diverse reranking for user={user_id}")

    # 4. If no relevant chunks survive reranking threshold
    if not chunks:
        logging.warning("RAG: No relevant chunks found for query.")
        return {
            "answer": "I couldn't find information about that in your uploaded documents.",
            "sources": [],
            "retrieved_chunks": []
        }

    # 5. Construct grounded context
    context_blocks = []
    for chunk in chunks:
        fn = chunk.get("metadata", {}).get("filename", "Document")
        pg = chunk.get("metadata", {}).get("page_number", 1)
        context_blocks.append(f"[Document: {fn}, Page: {pg}]\n{chunk['text']}")

    context = "\n\n---\n\n".join(context_blocks)

    # 6. Generate strictly grounded answer
    answer = generate_answer(question, context)

    # 7. Format source citations
    sources = []
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        sources.append({
            "filename": meta.get("filename", "Unknown Document"),
            "page_number": meta.get("page_number", 1),
            "chunk_number": meta.get("chunk_number", 0),
            "chunk_type": meta.get("chunk_type", "text"),
            "heading": meta.get("heading", ""),
            "rerank_score": round(chunk.get("rerank_score", 0.0), 3) if chunk.get("rerank_score") is not None else None,
            "snippet": chunk.get("text", "")[:280] + ("..." if len(chunk.get("text", "")) > 280 else "")
        })

    return {
        "answer": answer,
        "sources": sources,
        "retrieved_chunks": chunks
    }