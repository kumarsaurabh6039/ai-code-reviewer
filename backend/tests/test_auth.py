import time
import uuid

import jwt

from app.core.config import settings


def _email():
    return f"{uuid.uuid4().hex[:8]}@example.com"


def test_register_login_me(client):
    email = _email()
    r = client.post("/api/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 201
    assert client.post("/api/auth/register", json={"email": email, "password": "password123"}).status_code == 409
    tok = client.post("/api/auth/login", json={"email": email, "password": "password123"}).json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert me.status_code == 200 and me.json()["email"] == email


def test_wrong_password_and_missing_token(client):
    email = _email()
    client.post("/api/auth/register", json={"email": email, "password": "password123"})
    assert client.post("/api/auth/login", json={"email": email, "password": "wrongpass1"}).status_code == 401
    assert client.get("/api/auth/me").status_code == 401


def test_expired_token_rejected(client):
    expired = jwt.encode({"sub": "1", "exp": int(time.time()) - 10}, settings.secret_key, algorithm="HS256")
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401
