"""Authentication endpoints automated tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(async_client: AsyncClient):
    """Test successful user registration returns 200 with access and refresh tokens."""
    payload = {
        "email": "user@example.com",
        "password": "strongpassword123",
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client: AsyncClient):
    """Test duplicate registration returns 409 conflict."""
    payload = {
        "email": "dup@example.com",
        "password": "strongpassword123",
    }
    first_res = await async_client.post("/api/v1/auth/register", json=payload)
    assert first_res.status_code == 200

    second_res = await async_client.post("/api/v1/auth/register", json=payload)
    assert second_res.status_code == 409
    assert "already registered" in second_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_weak_password(async_client: AsyncClient):
    """Test registration with password shorter than 8 characters returns 422."""
    payload = {
        "email": "short@example.com",
        "password": "short",
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient):
    """Test login with valid credentials returns tokens."""
    reg_payload = {
        "email": "login_user@example.com",
        "password": "correctpassword123",
    }
    reg_res = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 200

    login_payload = {
        "email": "login_user@example.com",
        "password": "correctpassword123",
    }
    response = await async_client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password(async_client: AsyncClient):
    """Test login with wrong password returns 401 unauthorized."""
    reg_payload = {
        "email": "wrongpwd@example.com",
        "password": "correctpassword123",
    }
    await async_client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "wrongpwd@example.com",
        "password": "wrongpassword123",
    }
    response = await async_client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_invalid_email(async_client: AsyncClient):
    """Test login with nonexistent email returns 401 unauthorized."""
    login_payload = {
        "email": "nonexistent@example.com",
        "password": "somepassword123",
    }
    response = await async_client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(async_client: AsyncClient):
    """Test token refresh with valid refresh token returns a new access token."""
    reg_payload = {
        "email": "refresh_user@example.com",
        "password": "refreshpassword123",
    }
    reg_res = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 200
    refresh_tok = reg_res.json()["refresh_token"]

    refresh_payload = {"refresh_token": refresh_tok}
    response = await async_client.post("/api/v1/auth/refresh", json=refresh_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["access_token"]


@pytest.mark.asyncio
async def test_protected_route_no_token(async_client: AsyncClient):
    """Test accessing protected route GET /api/v1/auth/me without token returns 401."""
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_token(async_client: AsyncClient):
    """Test accessing protected route GET /api/v1/auth/me with valid token returns user info."""
    reg_payload = {
        "email": "me_user@example.com",
        "password": "password12345",
    }
    reg_res = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 200
    access_token = reg_res.json()["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    response = await async_client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me_user@example.com"
    assert data["role"] == "learner"
    assert "id" in data
    assert "created_at" in data
