import io
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def create_test_user():
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "Str0ngP@ssw0rd!"
    res = client.post("/auth/register", json={"email": email, "password": pwd})
    token = res.json()["access_token"]
    user_id = res.json()["user_id"]
    return {"email": email, "password": pwd, "token": token, "user_id": user_id}


def test_document_stats_and_list_empty():
    user = create_test_user()
    headers = {"Authorization": f"Bearer {user['token']}"}

    # 1. Check initial stats
    res = client.get("/documents/stats", headers=headers)
    assert res.status_code == 200
    stats = res.json()
    assert stats["total_documents"] == 0
    assert stats["completed_documents"] == 0

    # 2. Check initial document list
    doc_res = client.get("/documents", headers=headers)
    assert doc_res.status_code == 200
    assert doc_res.json() == []


def test_multi_user_document_isolation():
    user1 = create_test_user()
    user2 = create_test_user()

    headers1 = {"Authorization": f"Bearer {user1['token']}"}
    headers2 = {"Authorization": f"Bearer {user2['token']}"}

    # User 1 stats should be 0
    res1 = client.get("/documents", headers=headers1)
    assert res1.status_code == 200
    assert len(res1.json()) == 0

    # User 2 stats should be 0
    res2 = client.get("/documents", headers=headers2)
    assert res2.status_code == 200
    assert len(res2.json()) == 0


def test_chat_history_and_clear():
    user = create_test_user()
    headers = {"Authorization": f"Bearer {user['token']}"}

    # Check empty history
    h_res = client.get("/history", headers=headers)
    assert h_res.status_code == 200
    assert len(h_res.json()) == 0

    # Clear history
    del_res = client.delete("/history", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["message"] == "Chat history cleared successfully"
