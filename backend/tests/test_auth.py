"""Authentication endpoint tests."""

from httpx import AsyncClient

from tests.conftest import auth_headers, login, register_user


async def test_user_registration(client: AsyncClient) -> None:
    user = await register_user(
        client,
        role="AGENT",
        email="pytest-register@example.com",
        password="Register123!",
        full_name="Register Test",
    )

    assert user["body"]["email"] == "pytest-register@example.com"
    assert user["body"]["role"] == "AGENT"
    assert user["body"]["is_active"] is True
    assert "id" in user["body"]
    assert "created_at" in user["body"]


async def test_login_success(client: AsyncClient, admin_user: dict) -> None:
    token = await login(client, admin_user["email"], admin_user["password"])

    assert isinstance(token, str)
    assert len(token) > 0


async def test_login_failure_wrong_password(client: AsyncClient, admin_user: dict) -> None:
    response = await client.post(
        "/auth/login",
        data={"username": admin_user["email"], "password": "WrongPassword123!"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


async def test_auth_me_with_valid_token(client: AsyncClient, admin_user: dict, admin_token: str) -> None:
    response = await client.get("/auth/me", headers=auth_headers(admin_token))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == admin_user["id"]
    assert body["email"] == admin_user["email"]
    assert body["role"] == "ADMIN"


async def test_change_password(client: AsyncClient, agent_user: dict, agent_token: str) -> None:
    response = await client.post(
        "/auth/change-password",
        headers=auth_headers(agent_token),
        json={
            "current_password": agent_user["password"],
            "new_password": "NewAgent456!",
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully"

    # Old password should fail; new password should succeed.
    failed = await client.post(
        "/auth/login",
        data={"username": agent_user["email"], "password": agent_user["password"]},
    )
    assert failed.status_code == 401

    token = await login(client, agent_user["email"], "NewAgent456!")
    assert token
