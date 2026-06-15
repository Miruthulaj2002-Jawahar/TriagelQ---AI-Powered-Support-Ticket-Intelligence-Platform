"""Role-based access control tests for admin and agent users."""

from httpx import AsyncClient

from tests.conftest import auth_headers


async def _create_ticket(client: AsyncClient, token: str, **kwargs) -> dict:
    payload = {
        "title": kwargs.get("title", "RBAC ticket"),
        "description": kwargs.get("description", "RBAC test description"),
        "customer_email": kwargs.get("customer_email", "rbac@example.com"),
    }
    if "assigned_agent_id" in kwargs:
        payload["assigned_agent_id"] = kwargs["assigned_agent_id"]

    response = await client.post("/tickets", headers=auth_headers(token), json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def test_admin_can_list_users(client: AsyncClient, admin_token: str, agent_user: dict) -> None:
    response = await client.get("/users", headers=auth_headers(admin_token))

    assert response.status_code == 200
    emails = {user["email"] for user in response.json()}
    assert agent_user["email"] in emails


async def test_agent_cannot_list_users(client: AsyncClient, agent_token: str) -> None:
    response = await client.get("/users", headers=auth_headers(agent_token))

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


async def test_admin_can_access_analytics(client: AsyncClient, admin_token: str, agent_token: str) -> None:
    await _create_ticket(client, agent_token, title="Analytics ticket")

    response = await client.get("/analytics/summary", headers=auth_headers(admin_token))

    assert response.status_code == 200
    body = response.json()
    assert body["total_tickets"] >= 1
    assert "tickets_by_status" in body
    assert "resolution_rate" in body
    assert "ai_accuracy" in body
    assert "overridden_tickets" in body


async def test_agent_cannot_access_analytics(client: AsyncClient, agent_token: str) -> None:
    response = await client.get("/analytics/summary", headers=auth_headers(agent_token))

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


async def test_agent_cannot_access_unassigned_ticket(
    client: AsyncClient,
    admin_token: str,
    agent_token: str,
) -> None:
    ticket = await _create_ticket(
        client,
        admin_token,
        title="Admin-only visibility",
        description="No agent assignment",
    )
    assert ticket.get("assigned_agent_id") is None

    response = await client.get(
        f"/tickets/{ticket['id']}",
        headers=auth_headers(agent_token),
    )

    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


async def test_agent_cannot_update_non_status_fields(
    client: AsyncClient,
    agent_token: str,
) -> None:
    ticket = await _create_ticket(client, agent_token, title="Agent override attempt")

    response = await client.put(
        f"/tickets/{ticket['id']}",
        headers=auth_headers(agent_token),
        json={"priority": "URGENT"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Agents can only update ticket status"


async def test_agent_cannot_delete_ticket(client: AsyncClient, agent_token: str) -> None:
    ticket = await _create_ticket(client, agent_token, title="Delete forbidden")

    response = await client.delete(
        f"/tickets/{ticket['id']}",
        headers=auth_headers(agent_token),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


async def test_agent_cannot_access_other_agents_ticket(
    client: AsyncClient,
    admin_token: str,
    agent_user: dict,
    second_agent_user: dict,
    agent_token: str,
) -> None:
    ticket = await _create_ticket(
        client,
        admin_token,
        title="Assigned to first agent",
        assigned_agent_id=agent_user["id"],
    )

    second_token_response = await client.post(
        "/auth/login",
        data={"username": second_agent_user["email"], "password": second_agent_user["password"]},
    )
    assert second_token_response.status_code == 200
    second_token = second_token_response.json()["access_token"]

    response = await client.get(
        f"/tickets/{ticket['id']}",
        headers=auth_headers(second_token),
    )

    assert response.status_code == 403
