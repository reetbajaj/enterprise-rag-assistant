import time
import os
import io
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.document_service import process_pdf_background
from app.database.database import SessionLocal
from app.database.models import Document, User

client = TestClient(app)


def test_full_rag_pipeline_summary_and_user_isolation():
    # 1. Register User A and User B
    email_a = f"user_a_{uuid.uuid4().hex[:6]}@enterprise.ai"
    email_b = f"user_b_{uuid.uuid4().hex[:6]}@enterprise.ai"
    pwd = "Str0ngP@ssw0rd!"

    res_a = client.post("/auth/register", json={"email": email_a, "password": pwd})
    assert res_a.status_code == 201
    token_a = res_a.json()["access_token"]
    user_a_id = res_a.json()["user_id"]

    res_b = client.post("/auth/register", json={"email": email_b, "password": pwd})
    assert res_b.status_code == 201
    token_b = res_b.json()["access_token"]
    user_b_id = res_b.json()["user_b_id"] if "user_b_id" in res_b.json() else res_b.json()["user_id"]

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 2. Before upload: User A asks if documents exist -> Returns clear empty state
    pre_query = client.post(
        "/query",
        json={"question": "Do you have any documents uploaded?"},
        headers=headers_a
    )
    assert pre_query.status_code == 200
    assert "haven't uploaded any documents" in pre_query.json()["answer"].lower()

    # 3. Pick a real PDF from uploads for testing
    sample_pdf_path = "app/uploads/SafeEntry.pdf"
    if not os.path.exists(sample_pdf_path):
        for root, _, files in os.walk("app/uploads"):
            for f in files:
                if f.endswith(".pdf"):
                    sample_pdf_path = os.path.join(root, f)
                    break

    assert os.path.exists(sample_pdf_path), f"Sample PDF must exist at {sample_pdf_path}"

    with open(sample_pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # 4. User A uploads PDF
    upload_res = client.post(
        "/upload",
        files={"file": ("SafeEntry_Doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers_a
    )
    assert upload_res.status_code == 202
    doc_data = upload_res.json()
    doc_id = doc_data["document_id"]
    assert doc_data["status"] == "processing"

    # Synchronously run background indexing
    user_dir = os.path.join("app/uploads", f"user_{user_a_id}")
    saved_file_path = os.path.join(user_dir, "SafeEntry_Doc.pdf")
    process_pdf_background(
        document_id=doc_id,
        file_path=saved_file_path,
        filename="SafeEntry_Doc.pdf",
        user_id=user_a_id
    )

    # 5. After upload: User A asks if documents exist -> Returns document list
    post_cat_query = client.post(
        "/query",
        json={"question": "What documents do I have uploaded?"},
        headers=headers_a
    )
    assert post_cat_query.status_code == 200
    assert "SafeEntry_Doc.pdf" in post_cat_query.json()["answer"]

    # 6. User A asks broad summary query -> Returns grounded summary with citations
    summary_res = client.post(
        "/query",
        json={"question": "Summarize the key information in my uploaded documents."},
        headers=headers_a
    )
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert "i don't know based on the provided documents" not in summary_data["answer"].lower()
    assert len(summary_data["answer"]) > 20
    assert len(summary_data["sources"]) > 0

    # 7. User A asks specific factoid question -> Returns grounded answer with citations
    fact_res = client.post(
        "/query",
        json={"question": "What is SafeEntry or what is this document about?"},
        headers=headers_a
    )
    assert fact_res.status_code == 200
    fact_data = fact_res.json()
    assert len(fact_data["answer"]) > 5
    if fact_data["sources"]:
        src = fact_data["sources"][0]
        assert "filename" in src
        assert "page_number" in src

    # 8. User B (isolated) asks for summary -> No documents for User B
    b_summary = client.post(
        "/query",
        json={"question": "Summarize the key information in my uploaded documents."},
        headers=headers_b
    )
    assert b_summary.status_code == 200
    assert b_summary.json()["sources"] == []

    # 9. User A asks irrelevant question (lasagna recipe) -> Rejected without hallucination
    irrel_res = client.post(
        "/query",
        json={"question": "What is the secret recipe for Italian lasagna with mozzarella and beef?"},
        headers=headers_a
    )
    assert irrel_res.status_code == 200
    irrel_data = irrel_res.json()
    assert "couldn't find information" in irrel_data["answer"].lower() or len(irrel_data["sources"]) == 0

    # 10. Clean up document
    del_res = client.delete(f"/documents/{doc_id}", headers=headers_a)
    assert del_res.status_code == 200
