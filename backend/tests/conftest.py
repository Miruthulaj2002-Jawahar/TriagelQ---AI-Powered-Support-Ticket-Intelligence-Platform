"""
Shared pytest fixtures for the TriageIQ FastAPI backend.

Environment / database setup
------------------------------
Tests use a dedicated MongoDB database so production/dev data is not touched.

  - Default test DB name: triageiq_test
  - Override with: TEST_MONGODB_DB=my_custom_test_db
  - MongoDB URI comes from MONGODB_URI (defaults to mongodb://localhost:27017)
  - JWT_SECRET is required; a local-only default is set below if missing.

Safety guard: if TEST_MONGODB_DB resolves to the primary app database name
"triagemiq", collection tests abort unless ALLOW_PRODUCTION_TEST_DB=1 is set.

Prerequisites:
  1. MongoDB running and reachable at MONGODB_URI
  2. JWT_SECRET in .env or environment (or the pytest default below)
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

# Configure test environment BEFORE importing the FastAPI app (settings load at import).
_DEFAULT_TEST_DB = "triageiq_test"
_test_db_name = os.environ.get("TEST_MONGODB_DB", _DEFAULT_TEST_DB)
os.environ["MONGODB_DB"] = _test_db_name
os.environ.setdefault("JWT_SECRET", "pytest-local-jwt-secret-do-not-use-in-production")

if _test_db_name == "triagemiq" and os.environ.get("ALLOW_PRODUCTION_TEST_DB") != "1":
    pytest.exit(
        "Refusing to run tests against database 'triagemiq'. "
        "Set TEST_MONGODB_DB=triageiq_test (recommended) or "
        "ALLOW_PRODUCTION_TEST_DB=1 to override.",
        returncode=1,
    )

from app.db.mongodb import close_mongo_connection, connect_to_mongo, get_database  # noqa: E402
from app.main import app  # noqa: E402

TEST_ADMIN_PASSWORD = "TestAdmin123!"
TEST_AGENT_PASSWORD = "TestAgent123!"


async def login(client: AsyncClient, email: str, password: str) -> str:
    """Obtain a JWT access token via the OAuth2 login form."""
    response = await client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    """Build Authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {token}"}


async def register_user(
    client: AsyncClient,
    *,
    role: str,
    email: str | None = None,
    password: str | None = None,
    full_name: str | None = None,
) -> dict[str, Any]:
    """Register a user and return credentials plus the API response body."""
    resolved_email = email or f"pytest-{role.lower()}-{uuid.uuid4().hex[:12]}@example.com"
    resolved_password = password or (TEST_ADMIN_PASSWORD if role == "ADMIN" else TEST_AGENT_PASSWORD)
    resolved_name = full_name or f"Pytest {role.title()}"

    response = await client.post(
        "/auth/register",
        json={
            "full_name": resolved_name,
            "email": resolved_email,
            "password": resolved_password,
            "role": role,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return {
        "email": resolved_email,
        "password": resolved_password,
        "id": body["id"],
        "role": body["role"],
        "body": body,
    }


async def _clear_test_collections() -> None:
    db = get_database()
    await db.users.delete_many({})
    await db.tickets.delete_many({})


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Async HTTP client wired to the FastAPI app (httpx + ASGITransport).

    Clears the test database before and after each test for isolation.
    """
    await connect_to_mongo()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as async_client:
            await _clear_test_collections()
            yield async_client
            await _clear_test_collections()
    finally:
        await close_mongo_connection()


@pytest.fixture
async def admin_user(client: AsyncClient) -> dict[str, Any]:
    """Registered ADMIN user in the test database."""
    return await register_user(client, role="ADMIN")


@pytest.fixture
async def agent_user(client: AsyncClient) -> dict[str, Any]:
    """Registered AGENT user in the test database."""
    return await register_user(client, role="AGENT")


@pytest.fixture
async def admin_token(client: AsyncClient, admin_user: dict[str, Any]) -> str:
    """JWT for the test admin user."""
    return await login(client, admin_user["email"], admin_user["password"])


@pytest.fixture
async def agent_token(client: AsyncClient, agent_user: dict[str, Any]) -> str:
    """JWT for the test agent user."""
    return await login(client, agent_user["email"], agent_user["password"])


@pytest.fixture
async def second_agent_user(client: AsyncClient) -> dict[str, Any]:
    """Second AGENT user for cross-agent RBAC checks."""
    return await register_user(client, role="AGENT", full_name="Pytest Agent Two")
