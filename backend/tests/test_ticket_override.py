"""Manual AI override endpoint and analytics accuracy tests."""

from httpx import AsyncClient

from app.services.ticket_mapping import (
    compute_ai_accuracy_metrics,
    compute_effective_category,
    compute_effective_priority,
    resolve_ai_fields,
    ticket_has_real_override,
)
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


def test_effective_values_use_override_only_when_different() -> None:
    ticket = {
        "ai_category": "Billing",
        "ai_priority": "MEDIUM",
        "category_override": "Billing",
        "priority_override": "HIGH",
    }
    ai_fields = resolve_ai_fields(ticket)

    assert compute_effective_category(ticket, ai_fields) == "Billing"
    assert compute_effective_priority(ticket, ai_fields) == "HIGH"
    assert ticket_has_real_override(ticket, ai_fields) is True


def test_effective_values_fall_back_to_ai_when_no_override() -> None:
    ticket = {
        "ai_category": "Technical",
        "ai_priority": "LOW",
    }
    ai_fields = resolve_ai_fields(ticket)

    assert compute_effective_category(ticket, ai_fields) == "Technical"
    assert compute_effective_priority(ticket, ai_fields) == "LOW"
    assert ticket_has_real_override(ticket, ai_fields) is False


def test_compute_ai_accuracy_metrics_counts_real_overrides_only() -> None:
    tickets = [
        {
            "ai_category": "Billing",
            "ai_priority": "LOW",
            "category_override": "Technical",
        },
        {
            "ai_category": "General",
            "ai_priority": "MEDIUM",
            "category_override": "General",
            "priority_override": "MEDIUM",
        },
        {
            "ai_category": "Account",
            "ai_priority": "HIGH",
        },
    ]

    metrics = compute_ai_accuracy_metrics(tickets)

    assert metrics["total_classified_tickets"] == 3
    assert metrics["overridden_ticket_count"] == 1
    assert metrics["accepted_ai_count"] == 2
    assert metrics["override_rate"] == 33.33
    assert metrics["ai_accuracy"] == 66.67
    assert metrics["ai_classification_summary"] == {
        "Accepted AI Classification": 2,
        "Manually Overridden Classification": 1,
    }


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
    assert body["has_manual_override"] is True
    assert body["overridden_by_email"] == agent_user["email"]


async def test_admin_can_override_ticket(client: AsyncClient, admin_token: str) -> None:
    ticket = await _create_ticket(client, admin_token)
    new_priority = "URGENT" if ticket["ai_priority"] != "URGENT" else "LOW"

    response = await client.patch(
        f"/tickets/{ticket['id']}/override",
        headers=auth_headers(admin_token),
        json={"category": "Complaint", "priority": new_priority},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category_override"] == "Complaint"
    assert body["priority_override"] == new_priority
    assert body["ai_category"] == ticket["ai_category"]
    assert body["has_manual_override"] is True


async def test_override_rejects_matching_ai_values(
    client: AsyncClient,
    agent_token: str,
) -> None:
    ticket = await _create_ticket(client, agent_token)

    response = await client.patch(
        f"/tickets/{ticket['id']}/override",
        headers=auth_headers(agent_token),
        json={
            "category": ticket["ai_category"],
            "priority": ticket["ai_priority"],
        },
    )

    assert response.status_code == 400
    assert "match AI classification" in response.json()["detail"]


async def test_partial_override_stores_only_differing_fields(
    client: AsyncClient,
    agent_token: str,
) -> None:
    ticket = await _create_ticket(client, agent_token)

    response = await client.patch(
        f"/tickets/{ticket['id']}/override",
        headers=auth_headers(agent_token),
        json={
            "category": "Technical",
            "priority": ticket["ai_priority"],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["category_override"] == "Technical"
    assert body["priority_override"] is None
    assert body["priority"] == ticket["ai_priority"]
    assert body["has_manual_override"] is True


async def test_reset_override_clears_manual_fields(
    client: AsyncClient,
    agent_token: str,
) -> None:
    ticket = await _create_ticket(client, agent_token)

    override = await client.patch(
        f"/tickets/{ticket['id']}/override",
        headers=auth_headers(agent_token),
        json={"category": "Technical", "priority": "URGENT"},
    )
    assert override.status_code == 200

    reset = await client.delete(
        f"/tickets/{ticket['id']}/override",
        headers=auth_headers(agent_token),
    )
    assert reset.status_code == 200, reset.text

    body = reset.json()
    assert body["category"] == ticket["ai_category"]
    assert body["priority"] == ticket["ai_priority"]
    assert body["category_override"] is None
    assert body["priority_override"] is None
    assert body["override_reason"] is None
    assert body["overridden_by"] is None
    assert body["overridden_at"] is None
    assert body["has_manual_override"] is False
    assert body["ai_category"] == ticket["ai_category"]
    assert body["ai_priority"] == ticket["ai_priority"]


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


async def test_status_update_still_works_after_override(
    client: AsyncClient,
    agent_token: str,
) -> None:
    ticket = await _create_ticket(client, agent_token)

    override = await client.patch(
        f"/tickets/{ticket['id']}/override",
        headers=auth_headers(agent_token),
        json={"category": "Technical", "priority": "HIGH"},
    )
    assert override.status_code == 200

    update = await client.put(
        f"/tickets/{ticket['id']}",
        headers=auth_headers(agent_token),
        json={"status": "IN_PROGRESS"},
    )
    assert update.status_code == 200
    body = update.json()
    assert body["status"] == "IN_PROGRESS"
    assert body["has_manual_override"] is True
    assert body["category_override"] == "Technical"


async def test_analytics_ai_accuracy_updates(
    client: AsyncClient,
    admin_token: str,
    agent_token: str,
) -> None:
    ticket_one = await _create_ticket(client, agent_token, title="Override analytics A")
    await _create_ticket(client, agent_token, title="Override analytics B")

    before = await client.get("/analytics/summary", headers=auth_headers(admin_token))
    assert before.status_code == 200
    before_summary = before.json()
    assert before_summary["total_tickets"] >= 2
    assert before_summary["total_classified_tickets"] >= 2
    assert before_summary["accepted_ai_count"] == before_summary["total_classified_tickets"]
    assert before_summary["overridden_ticket_count"] == 0
    assert before_summary["override_rate"] == 0.0
    assert before_summary["ai_accuracy"] == 100.0

    override = await client.patch(
        f"/tickets/{ticket_one['id']}/override",
        headers=auth_headers(agent_token),
        json={"category": "Technical", "priority": "HIGH"},
    )
    assert override.status_code == 200

    after = await client.get("/analytics/summary", headers=auth_headers(admin_token))
    assert after.status_code == 200
    summary = after.json()
    assert summary["overridden_ticket_count"] >= 1
    assert summary["overridden_tickets"] == summary["overridden_ticket_count"]
    assert summary["accepted_ai_count"] == summary["total_classified_tickets"] - summary["overridden_ticket_count"]
    assert summary["override_rate"] > 0.0
    assert summary["ai_accuracy"] < 100.0
    assert summary["ai_classification_summary"]["Manually Overridden Classification"] >= 1
    assert summary["ai_classification_summary"]["Accepted AI Classification"] >= 1
