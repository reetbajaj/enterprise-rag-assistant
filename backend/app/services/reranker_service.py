import re
import logging
from sentence_transformers import CrossEncoder

reranker_model = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

MIN_FACTOID_SCORE = -5.0
MAX_CHUNKS_PER_DOC = 3
MAX_TOTAL_CHUNKS = 6


def rerank_chunks(question: str, chunks: list, is_summary: bool = False) -> list:
    """
    Reranks retrieved vector chunks using MS-MARCO CrossEncoder with document-diverse selection.
    Prevents single-document domination on multi-document or comparative queries.
    """
    if not chunks:
        return []

    # Detect if query explicitly asks for multi-document synthesis or broad summary
    is_multi_doc_summary = is_summary or bool(
        re.search(
            r"\b(both|all|each|across)\s+(uploaded\s+)?(documents?|files?|pdfs?)\b",
            question,
            re.IGNORECASE
        )
    )

    # If it is a generic multi-document summary without specific targeted names
    if is_summary:
        logging.info("Reranker: general summary mode active. Applying diverse per-document selection.")
        by_doc = {}
        for chunk in chunks:
            doc_id = chunk.get("metadata", {}).get("document_id", "default")
            chunk["rerank_score"] = round(1.0 - float(chunk.get("score", 0.0)), 3)
            by_doc.setdefault(doc_id, []).append(chunk)

        selected = []
        for doc_id, doc_chunks in by_doc.items():
            selected.extend(doc_chunks[:MAX_CHUNKS_PER_DOC])

        selected.sort(key=lambda x: x["rerank_score"], reverse=True)
        return selected[:MAX_TOTAL_CHUNKS]

    # Create question-chunk pairs for CrossEncoder
    pairs = [
        [question, chunk["text"]]
        for chunk in chunks
    ]

    try:
        scores = reranker_model.predict(pairs)
    except Exception as e:
        logging.error(f"Error during CrossEncoder reranking: {e}")
        return chunks[:MAX_TOTAL_CHUNKS]

    for index, score in enumerate(scores):
        chunks[index]["rerank_score"] = float(score)

    # Group candidate chunks by document to evaluate per-document relevance
    by_doc = {}
    for chunk in chunks:
        doc_id = chunk.get("metadata", {}).get("document_id", "default")
        by_doc.setdefault(doc_id, []).append(chunk)

    all_scored_docs = []
    for doc_id, doc_chunks in by_doc.items():
        doc_chunks.sort(key=lambda x: x["rerank_score"], reverse=True)
        top_score = doc_chunks[0]["rerank_score"]
        doc_name = doc_chunks[0].get("metadata", {}).get("filename", "Unknown")
        logging.info(f"Reranker: Doc '{doc_name}' top score = {top_score:.3f}")
        all_scored_docs.append((doc_id, doc_chunks, top_score))

    # Sort documents by their top relevance score
    all_scored_docs.sort(key=lambda x: x[2], reverse=True)

    # If the overall top document is below the relevance cutoff and not a multi-doc summary, reject all
    if not all_scored_docs or (all_scored_docs[0][2] < MIN_FACTOID_SCORE and not is_multi_doc_summary):
        logging.info(
            f"Overall top rerank score {all_scored_docs[0][2] if all_scored_docs else 'N/A'} is below {MIN_FACTOID_SCORE}. Discarding chunks."
        )
        return []

    # Select top chunks from each relevant document
    selected_chunks = []
    for doc_id, doc_chunks, top_score in all_scored_docs:
        if is_multi_doc_summary or top_score >= MIN_FACTOID_SCORE:
            valid_doc_chunks = [c for c in doc_chunks[:MAX_CHUNKS_PER_DOC] if (is_multi_doc_summary or c["rerank_score"] >= MIN_FACTOID_SCORE)]
            selected_chunks.extend(valid_doc_chunks)

    # Sort final selected pool by rerank score descending
    selected_chunks.sort(key=lambda x: x["rerank_score"], reverse=True)
    final_selection = selected_chunks[:MAX_TOTAL_CHUNKS]

    logging.info(
        f"Reranker: selected {len(final_selection)} balanced chunks across {len(set(c['metadata'].get('document_id') for c in final_selection))} document(s)."
    )
    return final_selection