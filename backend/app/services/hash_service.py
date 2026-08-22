import hashlib
import uuid


def compute_file_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as file:
        while True:
            chunk = file.read(8192)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


def generate_document_id(file_path: str, user_id: int = None) -> str:
    content_hash = compute_file_hash(file_path)[:16]
    random_suffix = uuid.uuid4().hex[:8]
    if user_id is not None:
        return f"doc_u{user_id}_{content_hash}_{random_suffix}"
    return f"doc_{content_hash}_{random_suffix}"