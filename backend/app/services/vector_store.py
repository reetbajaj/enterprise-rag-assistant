import chromadb

client = chromadb.PersistentClient(path="chroma_db")

collection = client.get_or_create_collection(
    name="documents"
)

def store_embeddings(
    document_id,
    filename,
    chunks,
    embeddings,
    user_id
):


    ids = [
        f"{document_id}_chunk_{i}"
        for i in range(len(chunks))
    ]


    metadatas = [
        {
            "document_id": document_id,
            "filename": filename,
            "page_number": chunk["page_number"],
            "chunk_number": i,
            "user_id": user_id
        }
        for i, chunk in enumerate(chunks)
    ]


    collection.add(
        ids=ids,
        documents=[
            chunk["text"]
            for chunk in chunks
        ],
        embeddings=embeddings,
        metadatas=metadatas
    )


def document_exists(document_id):
    result = collection.get(
        where={"document_id": document_id}
    )

    return len(result["ids"]) > 0

def delete_document(document_id):

    collection.delete(
        where={
            "document_id": document_id
        }
    )