from typing import Any

from app.schemas.ticket import TicketPriority, TicketResponse, TicketSentiment, TicketStatus


def resolve_ai_fields(ticket: dict[str, Any]) -> dict[str, Any]:
    """Resolve original AI fields, falling back to legacy ticket documents."""
    ai_category = ticket.get("ai_category")
    if ai_category is None:
        ai_category = ticket.get("category")

    ai_priority = ticket.get("ai_priority")
    if ai_priority is None:
        ai_priority = ticket.get("priority")

    ai_sentiment = ticket.get("ai_sentiment")
    if ai_sentiment is None:
        ai_sentiment = ticket.get("sentiment")

    ai_confidence = ticket.get("ai_confidence")
    if ai_confidence is None:
        ai_confidence = ticket.get("confidence", ticket.get("classification_confidence"))

    ai_explanation = ticket.get("ai_explanation")
    if ai_explanation is None:
        ai_explanation = ticket.get("explanation", ticket.get("classification_explanation"))

    return {
        "ai_category": ai_category,
        "ai_priority": ai_priority,
        "ai_sentiment": ai_sentiment,
        "ai_confidence": ai_confidence,
        "ai_explanation": ai_explanation,
    }


def compute_effective_category(ticket: dict[str, Any], ai_fields: dict[str, Any]) -> str | None:
    ai_category = ai_fields.get("ai_category")
    category_override = ticket.get("category_override")
    if category_override is not None and category_override != ai_category:
        return category_override
    return ai_category


def compute_effective_priority(ticket: dict[str, Any], ai_fields: dict[str, Any]) -> str | None:
    ai_priority = ai_fields.get("ai_priority")
    priority_override = ticket.get("priority_override")
    if priority_override is not None and priority_override != ai_priority:
        return priority_override
    return ai_priority


def ticket_has_real_override(ticket: dict[str, Any], ai_fields: dict[str, Any] | None = None) -> bool:
    ai = ai_fields or resolve_ai_fields(ticket)
    ai_category = ai.get("ai_category")
    ai_priority = ai.get("ai_priority")
    category_override = ticket.get("category_override")
    priority_override = ticket.get("priority_override")

    category_differs = (
        category_override is not None
        and ai_category is not None
        and category_override != ai_category
    )
    priority_differs = (
        priority_override is not None
        and ai_priority is not None
        and priority_override != ai_priority
    )
    return category_differs or priority_differs


def compute_ai_accuracy_metrics(tickets: list[dict[str, Any]]) -> dict[str, int | float]:
    total_classified = 0
    overridden_count = 0

    for ticket in tickets:
        ai_fields = resolve_ai_fields(ticket)
        if not ai_fields.get("ai_category") or not ai_fields.get("ai_priority"):
            continue

        total_classified += 1
        if ticket_has_real_override(ticket, ai_fields):
            overridden_count += 1

    accepted_count = max(total_classified - overridden_count, 0)
    if total_classified == 0:
        override_rate = 0.0
        ai_accuracy = 0.0
    else:
        override_rate = round((overridden_count / total_classified) * 100, 2)
        ai_accuracy = round((accepted_count / total_classified) * 100, 2)

    return {
        "total_classified_tickets": total_classified,
        "overridden_ticket_count": overridden_count,
        "accepted_ai_count": accepted_count,
        "override_rate": override_rate,
        "ai_accuracy": ai_accuracy,
        "ai_classification_summary": {
            "Accepted AI Classification": accepted_count,
            "Manually Overridden Classification": overridden_count,
        },
    }


def ticket_doc_to_response(
    ticket: dict[str, Any],
    *,
    overridden_by_name: str | None = None,
    overridden_by_email: str | None = None,
) -> TicketResponse:
    ai_fields = resolve_ai_fields(ticket)
    effective_category = compute_effective_category(ticket, ai_fields)
    effective_priority = compute_effective_priority(ticket, ai_fields)
    priority_override = ticket.get("priority_override")

    return TicketResponse(
        id=str(ticket["_id"]),
        title=ticket["title"],
        description=ticket["description"],
        customer_email=ticket["customer_email"],
        status=TicketStatus(ticket["status"]),
        category=effective_category,
        priority=TicketPriority(effective_priority) if effective_priority else TicketPriority(ticket["priority"]),
        sentiment=TicketSentiment(ticket["sentiment"]),
        assigned_queue=ticket.get("assigned_queue"),
        assigned_agent_id=ticket.get("assigned_agent_id"),
        created_by=ticket["created_by"],
        created_at=ticket["created_at"],
        updated_at=ticket["updated_at"],
        ai_category=ai_fields["ai_category"],
        ai_priority=TicketPriority(ai_fields["ai_priority"]) if ai_fields["ai_priority"] else None,
        ai_sentiment=TicketSentiment(ai_fields["ai_sentiment"]) if ai_fields["ai_sentiment"] else None,
        ai_confidence=ai_fields["ai_confidence"],
        ai_explanation=ai_fields["ai_explanation"],
        category_override=ticket.get("category_override"),
        priority_override=TicketPriority(priority_override) if priority_override else None,
        override_reason=ticket.get("override_reason"),
        overridden_by=ticket.get("overridden_by"),
        overridden_by_name=overridden_by_name,
        overridden_by_email=overridden_by_email,
        overridden_at=ticket.get("overridden_at"),
        has_manual_override=ticket_has_real_override(ticket, ai_fields),
    )


def build_ai_storage_fields(
    category: str,
    priority: str,
    sentiment: str,
    *,
    confidence: float | None = None,
    explanation: str | None = None,
) -> dict[str, Any]:
    default_explanation = (
        f"AI classified as {category} with {priority} priority and {sentiment} sentiment."
    )
    return {
        "ai_category": category,
        "ai_priority": priority,
        "ai_sentiment": sentiment,
        "ai_confidence": confidence,
        "ai_explanation": explanation or default_explanation,
    }
