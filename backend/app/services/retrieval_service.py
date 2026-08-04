from app.services.vector_store import collection
from app.services.embedding_service import model


def retrieve_chunks(
    query,
    user_id,
    k=5
):

    query_embedding = model.encode(query)


    results = collection.query(
        query_embeddings=[
            query_embedding.tolist()
        ],

        n_results=k,

        where={
            "user_id": user_id
        },

        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )


    retrieved_chunks = []


    if not results["documents"][0]:
        return []


    for i in range(
        len(results["documents"][0])
    ):

        retrieved_chunks.append(
            {
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "score": results["distances"][0][i]
            }
        )


    # Adaptive relevance filtering

    best_score = retrieved_chunks[0]["score"]

    score_threshold = best_score + 0.25


    filtered_chunks = [
        chunk
        for chunk in retrieved_chunks
        if chunk["score"] <= score_threshold
    ]


    return filtered_chunks