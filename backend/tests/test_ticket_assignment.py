"""Admin-to-agent ticket assignment tests."""

from httpx import AsyncClient

from tests.conftest import auth_headers


async def _create_ticket(
    client: AsyncClient,
    token: str,
    *,
    title: str = "Assignment test ticket",
    description: str = "Ticket used for assignment testing.",
    customer_email: str = "assign.customer@example.com",
    assigned_agent_id: str | None = None,
) -> dict:
    payload = {
        "title": title,
        "description": description,
        "customer_email": customer_email,
    }
    if assigned_agent_id is not None:
        payload["assigned_agent_id"] = assigned_agent_id

    response = await client.post(
        "/tickets",
        headers=auth_headers(token),
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_admin_can_assign_ticket_to_agent(
    client: AsyncClient,
    admin_token: str,
    agent_user: dict,
) -> None:
    ticket = await _create_ticket(
        client,
        admin_token,
        title="Admin assigned ticket",
        assigned_agent_id=agent_user["id"],
    )

    assert ticket["assigned_agent_id"] == agent_user["id"]
    assert ticket["assigned_agent_email"] == agent_user["email"]
    assert ticket["assigned_agent_name"] is not None


async def test_admin_assign_stores_email_on_ticket_document(
    client: AsyncClient,
    admin_token: str,
    agent_user: dict,
) -> None:
    ticket = await _create_ticket(
        client,
        admin_token,
        title="Persisted assignment email",
        assigned_agent_id=agent_user["id"],
    )

    detail = await client.get(
        f"/tickets/{ticket['id']}",
        headers=auth_headers(admin_token),
    )
    assert detail.status_code == 200
    assert detail.json()["assigned_agent_email"] == agent_user["email"]


async def test_agent_can_see_assigned_ticket(
    client: AsyncClient,
    admin_token: str,
    agent_token: str,
    agent_user: dict,
) -> None:
    ticket = await _create_ticket(
        client,
        admin_token,
        title="Visible to assigned agent",
        assigned_agent_id=agent_user["id"],
    )

    response = await client.get("/tickets", headers=auth_headers(agent_token))

    assert response.status_code == 200
    ticket_ids = {item["id"] for item in response.json()}
    assert ticket["id"] in ticket_ids


async def test_different_agent_cannot_see_assigned_ticket(
    client: AsyncClient,
    admin_token: str,
    agent_user: dict,
    second_agent_user: dict,
) -> None:
    ticket = await _create_ticket(
        client,
        admin_token,
        title="Assigned to first agent only",
        assigned_agent_id=agent_user["id"],
    )

    second_login = await client.post(
        "/auth/login",
        data={
            "username": second_agent_user["email"],
            "password": second_agent_user["password"],
        },
    )
    assert second_login.status_code == 200
    second_token = second_login.json()["access_token"]

    list_response = await client.get("/tickets", headers=auth_headers(second_token))
    assert list_response.status_code == 200
    assert ticket["id"] not in {item["id"] for item in list_response.json()}

    detail_response = await client.get(
        f"/tickets/{ticket['id']}",
        headers=auth_headers(second_token),
    )
    assert detail_response.status_code == 403


async def test_admin_cannot_assign_ticket_to_admin(
    client: AsyncClient,
    admin_token: str,
    admin_user: dict,
) -> None:
    response = await client.post(
        "/tickets",
        headers=auth_headers(admin_token),
        json={
            "title": "Invalid admin assignment",
            "description": "Should fail because target is an admin user.",
            "customer_email": "invalid.assign@example.com",
            "assigned_agent_id": admin_user["id"],
        },
    )

    assert response.status_code == 400
    assert "AGENT role" in response.json()["detail"]


async def test_admin_can_reassign_ticket(
    client: AsyncClient,
    admin_token: str,
    agent_user: dict,
    second_agent_user: dict,
) -> None:
    ticket = await _create_ticket(client, admin_token, assigned_agent_id=agent_user["id"])

    response = await client.put(
        f"/tickets/{ticket['id']}",
        headers=auth_headers(admin_token),
        json={"assigned_agent_id": second_agent_user["id"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assigned_agent_id"] == second_agent_user["id"]
    assert body["assigned_agent_email"] == second_agent_user["email"]


async def test_admin_can_unassign_ticket(
    client: AsyncClient,
    admin_token: str,
    agent_user: dict,
) -> None:
    ticket = await _create_ticket(client, admin_token, assigned_agent_id=agent_user["id"])

    response = await client.put(
        f"/tickets/{ticket['id']}",
        headers=auth_headers(admin_token),
        json={"assigned_agent_id": None},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assigned_agent_id"] is None
    assert body["assigned_agent_email"] is None


async def test_agent_cannot_change_assignment(
    client: AsyncClient,
    admin_token: str,
    agent_token: str,
    agent_user: dict,
    second_agent_user: dict,
) -> None:
    ticket = await _create_ticket(
        client,
        admin_token,
        assigned_agent_id=agent_user["id"],
    )

    response = await client.put(
        f"/tickets/{ticket['id']}",
        headers=auth_headers(agent_token),
        json={"assigned_agent_id": second_agent_user["id"]},
    )

    assert response.status_code == 403


async def test_admin_can_list_agents(
    client: AsyncClient,
    admin_token: str,
    agent_user: dict,
) -> None:
    response = await client.get("/users/agents", headers=auth_headers(admin_token))

    assert response.status_code == 200
    emails = {agent["email"] for agent in response.json()}
    assert agent_user["email"] in emails
    assert all(agent["role"] == "AGENT" for agent in response.json())


async def test_agent_cannot_list_agents(client: AsyncClient, agent_token: str) -> None:
    response = await client.get("/users/agents", headers=auth_headers(agent_token))

    assert response.status_code == 403
