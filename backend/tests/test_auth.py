import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_and_health():
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "running" in res_root.json()["message"]

    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"


def test_cors_preflight_options():
    res_reg_opt = client.options(
        "/auth/register",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }
    )
    assert res_reg_opt.status_code == 200
    assert res_reg_opt.headers.get("access-control-allow-origin") == "http://localhost:5173"

    res_login_opt = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:5175",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }
    )
    assert res_login_opt.status_code == 200
    assert res_login_opt.headers.get("access-control-allow-origin") == "http://localhost:5175"


def test_strong_password_requirements():
    import uuid
    email = f"test_pwd_{uuid.uuid4().hex[:6]}@enterprise.ai"

    # Too short (<8 chars)
    res_short = client.post("/auth/register", json={"email": email, "password": "Ab1!"})
    assert res_short.status_code == 400
    assert "at least 8 characters" in res_short.json()["detail"]

    # Missing uppercase
    res_no_upper = client.post("/auth/register", json={"email": email, "password": "password123!"})
    assert res_no_upper.status_code == 400
    assert "uppercase" in res_no_upper.json()["detail"]

    # Missing lowercase
    res_no_lower = client.post("/auth/register", json={"email": email, "password": "PASSWORD123!"})
    assert res_no_lower.status_code == 400
    assert "lowercase" in res_no_lower.json()["detail"]

    # Missing number
    res_no_num = client.post("/auth/register", json={"email": email, "password": "Password!!!!"})
    assert res_no_num.status_code == 400
    assert "number" in res_no_num.json()["detail"]

    # Missing special character
    res_no_spec = client.post("/auth/register", json={"email": email, "password": "Password123"})
    assert res_no_spec.status_code == 400
    assert "special character" in res_no_spec.json()["detail"]

    # Strong password passes
    res_valid = client.post("/auth/register", json={"email": email, "password": "Str0ngP@ssw0rd!"})
    assert res_valid.status_code == 201
    assert "access_token" in res_valid.json()


def test_auth_registration_and_login_flow():
    import uuid
    email = f"test_user_{uuid.uuid4().hex[:6]}@enterprise.ai"
    pwd = "Str0ngP@ssw0rd!"

    # 1. Register
    reg_res = client.post("/auth/register", json={"email": email, "password": pwd})
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    user_id = reg_res.json()["user_id"]
    assert token is not None

    # 2. Duplicate registration fails (409)
    dup_res = client.post("/auth/register", json={"email": email, "password": pwd})
    assert dup_res.status_code == 409

    # 3. Login with valid credentials (JSON)
    login_res = client.post("/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    assert login_res.json()["access_token"] is not None

    # 4. Login with invalid password fails (401)
    bad_login = client.post("/auth/login", json={"email": email, "password": "WrongP@ssword123!"})
    assert bad_login.status_code == 401

    # 5. Access protected /auth/me with Bearer token
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # 6. Access protected route without token fails (401)
    unauth_res = client.get("/auth/me")
    assert unauth_res.status_code == 401
