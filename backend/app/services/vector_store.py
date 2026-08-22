import chromadb
import logging
from typing import List, Dict, Any

client = chromadb.PersistentClient(
    path="chroma_db"
)

collection = client.get_or_create_collection(
    name="documents"
)


def store_embeddings(
    document_id: str,
    filename: str,
    chunks: List[Dict[str, Any]],
    embeddings: Any,
    user_id: int
):
    if not chunks:
        return

    ids = [
        f"u{user_id}_{document_id}_chunk_{i}"
        for i in range(len(chunks))
    ]

    metadatas = []
    documents = []

    for i, chunk in enumerate(chunks):
        content_type = str(chunk.get("content_type") or chunk.get("chunk_type") or "text")
        source_type = str(chunk.get("source_type") or "pdf_text")
        metadata = {
            "document_id": str(document_id),
            "filename": str(filename),
            "page_number": int(chunk.get("page_number", 1)),
            "chunk_number": int(i),
            "user_id": int(user_id),
            "content_type": content_type,
            "source_type": source_type,
            "chunk_type": str(chunk.get("chunk_type", "text") or "text"),
            "heading": str(chunk.get("heading") or ""),
            "has_images": str(chunk.get("has_images", False))
        }
        metadatas.append(metadata)
        documents.append(chunk["text"])

    embedding_list = [
        emb.tolist() if hasattr(emb, "tolist") else list(emb)
        for emb in embeddings
    ]

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embedding_list,
        metadatas=metadatas
    )
    logging.info(f"Stored {len(chunks)} multimodal chunks for doc {document_id} (user={user_id})")


def document_exists(document_id: str, user_id: int) -> bool:
    try:
        result = collection.get(
            where={
                "$and": [
                    {"document_id": str(document_id)},
                    {"user_id": int(user_id)}
                ]
            },
            limit=1
        )
        return bool(result and result.get("ids") and len(result["ids"]) > 0)
    except Exception as e:
        logging.warning(f"Error checking document existence in Chroma: {e}")
        return False


def delete_document(document_id: str, user_id: int):
    try:
        collection.delete(
            where={
                "$and": [
                    {"document_id": str(document_id)},
                    {"user_id": int(user_id)}
                ]
            }
        )
        logging.info(f"Deleted chunks for doc {document_id} (user={user_id})")
    except Exception as e:
        logging.error(f"Failed to delete document {document_id} from vector store: {e}")
        raise e


def count_user_chunks(user_id: int) -> int:
    try:
        result = collection.get(
            where={"user_id": int(user_id)},
            include=[]
        )
        return len(result.get("ids", []))
    except Exception:
        return 0