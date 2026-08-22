import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_multi_conversation_crud_and_isolation():
    # 1. Register User 1 and User 2
    u1_email = f"user1_{uuid.uuid4().hex[:6]}@enterprise.ai"
    u2_email = f"user2_{uuid.uuid4().hex[:6]}@enterprise.ai"
    pwd = "Str0ngP@ssw0rd!"

    res1 = client.post("/auth/register", json={"email": u1_email, "password": pwd})
    token1 = res1.json()["access_token"]
    h1 = {"Authorization": f"Bearer {token1}"}

    res2 = client.post("/auth/register", json={"email": u2_email, "password": pwd})
    token2 = res2.json()["access_token"]
    h2 = {"Authorization": f"Bearer {token2}"}

    # 2. User 1 creates Conversation A
    res_conv_a = client.post("/conversations", json={"title": "Project Architecture"}, headers=h1)
    assert res_conv_a.status_code == 201
    conv_a_id = res_conv_a.json()["id"]
    assert res_conv_a.json()["title"] == "Project Architecture"

    # User 1 creates Conversation B
    res_conv_b = client.post("/conversations", json={"title": "Policy Questions"}, headers=h1)
    assert res_conv_b.status_code == 201
    conv_b_id = res_conv_b.json()["id"]

    # 3. User 1 queries in Conversation A
    q_res = client.post(
        "/query",
        json={"question": "Do you have any documents uploaded?", "conversation_id": conv_a_id},
        headers=h1
    )
    assert q_res.status_code == 200
    assert q_res.json()["conversation_id"] == conv_a_id

    # 4. User 1 retrieves Conversation A details with messages
    get_a = client.get(f"/conversations/{conv_a_id}", headers=h1)
    assert get_a.status_code == 200
    msgs_a = get_a.json()["messages"]
    assert len(msgs_a) >= 2  # user message and assistant message
    assert msgs_a[0]["role"] == "user"
    assert msgs_a[1]["role"] == "assistant"

    # 5. User 2 cannot access User 1's conversation (404)
    u2_get = client.get(f"/conversations/{conv_a_id}", headers=h2)
    assert u2_get.status_code == 404

    # 6. User 1 renames Conversation A
    rename_res = client.patch(
        f"/conversations/{conv_a_id}",
        json={"title": "Renamed System Architecture"},
        headers=h1
    )
    assert rename_res.status_code == 200
    assert rename_res.json()["title"] == "Renamed System Architecture"

    # 7. User 1 lists all conversations
    list_res = client.get("/conversations", headers=h1)
    assert list_res.status_code == 200
    conv_list = list_res.json()
    assert len(conv_list) == 2
    assert any(c["id"] == conv_a_id for c in conv_list)
    assert any(c["id"] == conv_b_id for c in conv_list)

    # 8. User 1 deletes Conversation A
    del_res = client.delete(f"/conversations/{conv_a_id}", headers=h1)
    assert del_res.status_code == 200

    # Verify Conversation A is gone and Conversation B remains
    list_after = client.get("/conversations", headers=h1)
    assert len(list_after.json()) == 1
    assert list_after.json()[0]["id"] == conv_b_id

    # 9. User 1 clears all conversations
    clear_res = client.delete("/conversations", headers=h1)
    assert clear_res.status_code == 200
    assert len(client.get("/conversations", headers=h1).json()) == 0
