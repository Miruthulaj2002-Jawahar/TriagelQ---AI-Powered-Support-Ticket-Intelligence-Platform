"""
Core API integration tests for TriageIQ.

Uses httpx AsyncClient against the FastAPI app with an isolated MongoDB
database (see tests/conftest.py).
"""

from httpx import AsyncClient

from tests.conftest import auth_headers, login, register_user


async def test_integration_register_user(client: AsyncClient) -> None:
    user = await register_user(
        client,
        role="AGENT",
        email="integration-agent@example.com",
        password="Integration123!",
        full_name="Integration Agent",
    )

    assert user["body"]["email"] == "integration-agent@example.com"
    assert user["body"]["role"] == "AGENT"


async def test_integration_login_returns_jwt(client: AsyncClient, admin_user: dict) -> None:
    token = await login(client, admin_user["email"], admin_user["password"])

    me = await client.get("/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["email"] == admin_user["email"]


async def test_integration_create_ticket_with_classification(
    client: AsyncClient,
    agent_token: str,
) -> None:
    response = await client.post(
        "/tickets",
        headers=auth_headers(agent_token),
        json={
            "title": "Urgent billing refund",
            "description": "Customer was charged twice on invoice and needs urgent refund.",
            "customer_email": "integration.customer@example.com",
        },
    )

    assert response.status_code == 201, response.text
    ticket = response.json()
    assert ticket["ai_category"] == "Billing"
    assert ticket["ai_priority"] is not None
    assert ticket["ai_sentiment"] is not None
    assert ticket["ai_confidence"] is not None
    assert ticket["ai_explanation"] is not None
    assert ticket["assigned_queue"] == "Escalations"


async def test_integration_get_tickets_authenticated(
    client: AsyncClient,
    agent_token: str,
) -> None:
    create = await client.post(
        "/tickets",
        headers=auth_headers(agent_token),
        json={
            "title": "Integration list ticket",
            "description": "General support question for list endpoint test.",
            "customer_email": "list.customer@example.com",
        },
    )
    assert create.status_code == 201

    response = await client.get("/tickets", headers=auth_headers(agent_token))

    assert response.status_code == 200
    titles = {ticket["title"] for ticket in response.json()}
    assert "Integration list ticket" in titles


async def test_integration_admin_analytics_summary(
    client: AsyncClient,
    admin_token: str,
    agent_token: str,
) -> None:
    create = await client.post(
        "/tickets",
        headers=auth_headers(agent_token),
        json={
            "title": "Analytics integration ticket",
            "description": "Technical error on dashboard load.",
            "customer_email": "analytics.customer@example.com",
        },
    )
    assert create.status_code == 201

    response = await client.get("/analytics/summary", headers=auth_headers(admin_token))

    assert response.status_code == 200
    summary = response.json()
    assert summary["total_tickets"] >= 1
    assert "ai_accuracy" in summary
    assert "override_rate" in summary
    assert "total_classified_tickets" in summary


async def test_integration_agent_cannot_access_admin_users(
    client: AsyncClient,
    agent_token: str,
) -> None:
    response = await client.get("/users", headers=auth_headers(agent_token))

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"
