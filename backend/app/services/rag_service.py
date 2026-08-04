from app.services.retrieval_service import retrieve_chunks
from app.services.llm_service import generate_answer
import logging


def answer_question(question, user_id):

    logging.info(
        f"User {user_id} query: {question}"
    )


    chunks = retrieve_chunks(
        question,
        user_id
    )


    logging.info(
        f"Retrieved {len(chunks)} chunks for user {user_id}"
    )


    if not chunks:

        logging.warning(
            "No relevant chunks found"
        )

        return {
            "answer": "I don't know based on the provided documents.",
            "sources": []
        }


    best_score = chunks[0]["score"]


    logging.info(
        f"Best retrieval score: {best_score}"
    )


    if best_score > 1.8:

        logging.warning(
            "Retrieval confidence too low"
        )

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


    logging.info(
        "Answer generated successfully"
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