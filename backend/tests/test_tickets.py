"""Ticket CRUD and status update tests."""

from httpx import AsyncClient

from tests.conftest import auth_headers


async def _create_ticket(
    client: AsyncClient,
    token: str,
    *,
    title: str = "Test ticket",
    description: str = "General support question",
    customer_email: str = "customer@example.com",
) -> dict:
    response = await client.post(
        "/tickets",
        headers=auth_headers(token),
        json={
            "title": title,
            "description": description,
            "customer_email": customer_email,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_ticket_creation(client: AsyncClient, agent_token: str, agent_user: dict) -> None:
    ticket = await _create_ticket(
        client,
        agent_token,
        title="Cannot login to account",
        description="User cannot access account after password reset.",
    )

    assert ticket["title"] == "Cannot login to account"
    assert ticket["status"] == "OPEN"
    assert ticket["created_by"] == agent_user["id"]
    assert ticket["assigned_agent_id"] == agent_user["id"]
    assert ticket["category"] is not None
    assert ticket["priority"] in {"LOW", "MEDIUM", "HIGH", "URGENT"}
    assert ticket["sentiment"] in {"POSITIVE", "NEUTRAL", "NEGATIVE"}
    assert ticket["ai_category"] is not None
    assert ticket["ai_priority"] is not None
    assert ticket["ai_sentiment"] is not None
    assert ticket["ai_confidence"] is not None
    assert ticket["ai_explanation"] is not None


async def test_ticket_list_access_admin_sees_all(
    client: AsyncClient,
    admin_token: str,
    agent_token: str,
) -> None:
    await _create_ticket(client, agent_token, title="Agent ticket A")
    await _create_ticket(client, admin_token, title="Admin ticket B")

    response = await client.get("/tickets", headers=auth_headers(admin_token))

    assert response.status_code == 200
    titles = {ticket["title"] for ticket in response.json()}
    assert "Agent ticket A" in titles
    assert "Admin ticket B" in titles


async def test_ticket_list_access_agent_sees_assigned_only(
    client: AsyncClient,
    admin_token: str,
    agent_token: str,
    agent_user: dict,
) -> None:
    assigned = await _create_ticket(client, agent_token, title="Assigned to agent")
    await _create_ticket(
        client,
        admin_token,
        title="Unassigned admin ticket",
        description="Created by admin without assignment",
    )

    response = await client.get("/tickets", headers=auth_headers(agent_token))

    assert response.status_code == 200
    tickets = response.json()
    assert len(tickets) == 1
    assert tickets[0]["id"] == assigned["id"]
    assert tickets[0]["assigned_agent_id"] == agent_user["id"]


async def test_ticket_detail_access(client: AsyncClient, agent_token: str) -> None:
    created = await _create_ticket(client, agent_token, title="Detail test ticket")

    response = await client.get(
        f"/tickets/{created['id']}",
        headers=auth_headers(agent_token),
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["title"] == "Detail test ticket"


async def test_ticket_status_update(client: AsyncClient, agent_token: str) -> None:
    created = await _create_ticket(client, agent_token, title="Status update ticket")

    response = await client.put(
        f"/tickets/{created['id']}",
        headers=auth_headers(agent_token),
        json={"status": "IN_PROGRESS"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "IN_PROGRESS"
