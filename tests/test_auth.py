import pytest


@pytest.mark.asyncio
async def test_register_and_login(client):
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "alice@example.com", "password": "password123", "full_name": "Alice"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "alice@example.com"

    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["refresh_token"]

    refresh = body["refresh_token"]
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    new_body = r.json()
    assert new_body["access_token"] and new_body["refresh_token"]


@pytest.mark.asyncio
async def test_register_duplicate_email_conflict(client):
    payload = {"email": "dup@example.com", "password": "password123"}
    r1 = await client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "bob@example.com", "password": "password123"},
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "bob@example.com", "password": "wrongpassword"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    r = await client.get("/api/v1/users/me")
    assert r.status_code == 403 or r.status_code == 401


@pytest.mark.asyncio
async def test_me_with_valid_token(auth_client, test_user):
    r = await auth_client.get("/api/v1/users/me")
    assert r.status_code == 200
    assert r.json()["id"] == str(test_user.id)
