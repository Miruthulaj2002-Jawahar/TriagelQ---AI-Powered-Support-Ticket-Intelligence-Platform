"""Admin user management endpoint tests."""

import uuid

import pytest
from httpx import AsyncClient

import app.routers.users as users_router
from tests.conftest import auth_headers, login


async def _create_user_via_api(
    client: AsyncClient,
    admin_token: str,
    *,
    role: str = "AGENT",
    email: str | None = None,
    password: str = "CreatedUser123!",
    name: str = "Created User",
) -> dict:
    resolved_email = email or f"pytest-created-{uuid.uuid4().hex[:10]}@example.com"
    response = await client.post(
        "/users",
        headers=auth_headers(admin_token),
        json={
            "name": name,
            "email": resolved_email,
            "password": password,
            "role": role,
        },
    )
    assert response.status_code == 201, response.text
    return {"email": resolved_email, "password": password, **response.json()}


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


async def test_admin_can_deactivate_user(
    client: AsyncClient,
    admin_token: str,
    agent_user: dict,
) -> None:
    response = await client.delete(
        f"/users/{agent_user['id']}",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == agent_user["id"]
    assert body["is_active"] is False


async def test_agent_cannot_deactivate_user(
    client: AsyncClient,
    agent_token: str,
    admin_user: dict,
) -> None:
    response = await client.delete(
        f"/users/{admin_user['id']}",
        headers=auth_headers(agent_token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


async def test_unauthenticated_cannot_deactivate_user(
    client: AsyncClient,
    agent_user: dict,
) -> None:
    response = await client.delete(f"/users/{agent_user['id']}")

    assert response.status_code == 401


async def test_admin_cannot_deactivate_self(
    client: AsyncClient,
    admin_token: str,
    admin_user: dict,
) -> None:
    response = await client.delete(
        f"/users/{admin_user['id']}",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "You cannot deactivate your own account"


async def test_admin_cannot_deactivate_last_active_admin(
    client: AsyncClient,
    admin_token: str,
    admin_user: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    second_admin = await _create_user_via_api(
        client,
        admin_token,
        role="ADMIN",
        name="Second Admin",
        password="SecondAdmin123!",
    )
    second_admin_token = await login(
        client,
        second_admin["email"],
        second_admin["password"],
    )

    async def mock_count_active_admins(_db) -> int:
        return 1

    monkeypatch.setattr(users_router, "count_active_admins", mock_count_active_admins)

    response = await client.delete(
        f"/users/{admin_user['id']}",
        headers=auth_headers(second_admin_token),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot deactivate the last active admin"


async def test_deactivated_user_cannot_login(
    client: AsyncClient,
    admin_token: str,
) -> None:
    created = await _create_user_via_api(
        client,
        admin_token,
        role="AGENT",
        name="Login Blocked Agent",
        password="LoginBlocked123!",
    )

    deactivate_response = await client.delete(
        f"/users/{created['id']}",
        headers=auth_headers(admin_token),
    )
    assert deactivate_response.status_code == 200

    login_response = await client.post(
        "/auth/login",
        data={"username": created["email"], "password": created["password"]},
    )

    assert login_response.status_code == 403
    assert login_response.json()["detail"] == "Inactive user account"
