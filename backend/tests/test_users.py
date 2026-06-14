"""Admin user creation endpoint tests."""

import uuid

from httpx import AsyncClient

from tests.conftest import auth_headers


async def test_admin_can_create_user(client: AsyncClient, admin_token: str) -> None:
    email = f"pytest-created-{uuid.uuid4().hex[:10]}@example.com"

    response = await client.post(
        "/users",
        headers=auth_headers(admin_token),
        json={
            "name": "Created Agent",
            "email": email,
            "password": "CreatedAgent123!",
            "role": "AGENT",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Created Agent"
    assert body["email"] == email
    assert body["role"] == "AGENT"
    assert "id" in body
    assert "created_at" in body
    assert "password" not in body
    assert "hashed_password" not in body


async def test_agent_cannot_create_user(client: AsyncClient, agent_token: str) -> None:
    response = await client.post(
        "/users",
        headers=auth_headers(agent_token),
        json={
            "name": "Blocked User",
            "email": f"pytest-blocked-{uuid.uuid4().hex[:10]}@example.com",
            "password": "BlockedUser123!",
            "role": "AGENT",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


async def test_unauthenticated_cannot_create_user(client: AsyncClient) -> None:
    response = await client.post(
        "/users",
        json={
            "name": "No Auth User",
            "email": f"pytest-noauth-{uuid.uuid4().hex[:10]}@example.com",
            "password": "NoAuthUser123!",
            "role": "AGENT",
        },
    )

    assert response.status_code == 401


async def test_create_user_duplicate_email_rejected(
    client: AsyncClient,
    admin_token: str,
    agent_user: dict,
) -> None:
    response = await client.post(
        "/users",
        headers=auth_headers(admin_token),
        json={
            "name": "Duplicate Email",
            "email": agent_user["email"],
            "password": "DuplicateEmail123!",
            "role": "AGENT",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"
