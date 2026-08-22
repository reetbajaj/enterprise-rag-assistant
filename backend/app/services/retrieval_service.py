import logging
from app.services.vector_store import collection
from app.services.embedding_service import model
from app.services.reranker_service import rerank_chunks


def retrieve_chunks(
    query: str,
    user_id: int,
    k: int = 10,
    is_summary: bool = False
) -> list:
    """
    Retrieves semantic vector candidates from ChromaDB with strict user isolation,
    logs detailed candidate telemetry, then applies document-diverse CrossEncoder reranking.
    """
    logging.info(f"Retrieval: querying ChromaDB for user={user_id}, query='{query}'")

    query_embedding = model.encode(query)

    # Fetch larger candidate pool to ensure multi-document representation
    fetch_k = max(25, k * 2)

    try:
        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=fetch_k,
            where={"user_id": user_id},
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        logging.error(f"ChromaDB retrieval query failed for user {user_id}: {e}")
        return []

    if not results or not results.get("documents") or not results["documents"][0]:
        logging.info(f"ChromaDB returned 0 chunks for user={user_id}")
        return []

    retrieved_chunks = []
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    for i in range(len(docs)):
        retrieved_chunks.append({
            "text": docs[i],
            "metadata": metas[i],
            "score": distances[i]
        })

    # Structured Debug Logging as requested
    log_lines = [f"\nQUERY:\n{query}\n\nRETRIEVED RESULTS:"]
    for idx, c in enumerate(retrieved_chunks):
        m = c.get("metadata", {})
        fn = m.get("filename", "Unknown")
        did = m.get("document_id", "Unknown")
        pg = m.get("page_number", 1)
        dist = c.get("score", 0.0)
        log_lines.append(
            f"{idx + 1}. document_name = {fn}\n   document_id = {did}\n   page = {pg}\n   score/distance = {dist:.4f}"
        )

    logging.info("\n".join(log_lines))

    # Apply document-diverse reranking
    reranked_chunks = rerank_chunks(
        query,
        retrieved_chunks,
        is_summary=is_summary
    )

    return reranked_chunks