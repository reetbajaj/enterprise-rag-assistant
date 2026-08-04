from app.services.retrieval_service import retrieve_chunks
from app.services.llm_service import generate_answer


def answer_question(question,user_id):

    chunks = retrieve_chunks(question,user_id)
    if not chunks:
        return {
            "answer": "I don't know based on the provided documents.",
            "sources": []
        }
    
    best_score = chunks[0]["score"]

    if best_score > 1.8:
        return {
            "answer": "I don't know based on the provided documents.",
            "sources": []
        }


    context = "\n\n".join(
    [
        f"""
        Source: {chunk['metadata']['filename']}
        Chunk: {chunk['metadata']['chunk_number']}

        {chunk['text']}
        """
        for chunk in chunks
    ]
    )


    answer = generate_answer(
        question,
        context
    )


    sources = []

    for chunk in chunks:
        sources.append({
            "filename": chunk["metadata"]["filename"],
            "page_number": chunk["metadata"]["page_number"],
            "chunk_number": chunk["metadata"]["chunk_number"]
        })


    return {
        "answer": answer,
        "sources": sources,
        "retrieved_chunks": chunks
    }