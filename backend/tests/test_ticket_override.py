"""Manual AI override endpoint tests."""

from httpx import AsyncClient

from tests.conftest import auth_headers


async def _create_ticket(
    client: AsyncClient,
    token: str,
    *,
    title: str = "Billing refund issue",
    description: str = "Customer needs a refund for duplicate billing charge on invoice.",
) -> dict:
    response = await client.post(
        "/tickets",
        headers=auth_headers(token),
        json={
            "title": title,
            "description": description,
            "customer_email": "override.customer@example.com",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_agent_can_override_assigned_ticket(
    client: AsyncClient,
    agent_token: str,
    agent_user: dict,
) -> None:
    ticket = await _create_ticket(client, agent_token)
    original_ai_category = ticket["ai_category"]
    original_ai_priority = ticket["ai_priority"]

    response = await client.patch(
        f"/tickets/{ticket['id']}/override",
        headers=auth_headers(agent_token),
        json={
            "category": "Technical",
            "priority": "URGENT",
            "override_reason": "Customer clarified this is a production outage.",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ai_category"] == original_ai_category
    assert body["ai_priority"] == original_ai_priority
    assert body["category"] == "Technical"
    assert body["priority"] == "URGENT"
    assert body["category_override"] == "Technical"
    assert body["priority_override"] == "URGENT"
    assert body["override_reason"] == "Customer clarified this is a production outage."
    assert body["overridden_by"] == agent_user["id"]
    assert body["overridden_at"] is not None


async def test_admin_can_override_ticket(client: AsyncClient, admin_token: str) -> None:
    ticket = await _create_ticket(client, admin_token)

    response = await client.patch(
        f"/tickets/{ticket['id']}/override",
        headers=auth_headers(admin_token),
        json={"category": "Complaint", "priority": "HIGH"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category_override"] == "Complaint"
    assert body["priority_override"] == "HIGH"
    assert body["ai_category"] == ticket["ai_category"]


async def test_override_rejects_invalid_category(
    client: AsyncClient,
    agent_token: str,
) -> None:
    ticket = await _create_ticket(client, agent_token)

    response = await client.patch(
        f"/tickets/{ticket['id']}/override",
        headers=auth_headers(agent_token),
        json={"category": "Not A Real Category", "priority": "LOW"},
    )

    assert response.status_code == 400
    assert "Invalid category" in response.json()["detail"]


async def test_override_rejects_invalid_priority(
    client: AsyncClient,
    agent_token: str,
) -> None:
    ticket = await _create_ticket(client, agent_token)

    response = await client.patch(
        f"/tickets/{ticket['id']}/override",
        headers=auth_headers(agent_token),
        json={"category": "Billing", "priority": "SUPER_URGENT"},
    )

    assert response.status_code == 422


async def test_agent_cannot_override_unassigned_ticket(
    client: AsyncClient,
    admin_token: str,
    agent_token: str,
) -> None:
    ticket = await _create_ticket(
        client,
        admin_token,
        title="Unassigned admin ticket",
        description="Created without agent assignment.",
    )

    response = await client.patch(
        f"/tickets/{ticket['id']}/override",
        headers=auth_headers(agent_token),
        json={"category": "Technical", "priority": "HIGH"},
    )

    assert response.status_code == 403


async def test_analytics_ai_accuracy_updates(
    client: AsyncClient,
    admin_token: str,
    agent_token: str,
) -> None:
    ticket_one = await _create_ticket(client, agent_token, title="Override analytics A")
    await _create_ticket(client, agent_token, title="Override analytics B")

    before = await client.get("/analytics/summary", headers=auth_headers(admin_token))
    assert before.status_code == 200
    assert before.json()["total_tickets"] >= 2
    assert before.json()["ai_accuracy"] == 100.0

    override = await client.patch(
        f"/tickets/{ticket_one['id']}/override",
        headers=auth_headers(agent_token),
        json={"category": "Technical", "priority": "HIGH"},
    )
    assert override.status_code == 200

    after = await client.get("/analytics/summary", headers=auth_headers(admin_token))
    assert after.status_code == 200
    summary = after.json()
    assert summary["overridden_tickets"] >= 1
    assert summary["ai_accuracy"] < 100.0
