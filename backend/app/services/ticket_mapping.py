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


def ticket_doc_to_response(ticket: dict[str, Any]) -> TicketResponse:
    ai_fields = resolve_ai_fields(ticket)
    priority_override = ticket.get("priority_override")

    return TicketResponse(
        id=str(ticket["_id"]),
        title=ticket["title"],
        description=ticket["description"],
        customer_email=ticket["customer_email"],
        status=TicketStatus(ticket["status"]),
        category=ticket.get("category"),
        priority=TicketPriority(ticket["priority"]),
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
        overridden_at=ticket.get("overridden_at"),
    )


def build_ai_storage_fields(
    category: str,
    priority: str,
    sentiment: str,
) -> dict[str, Any]:
    explanation = (
        f"AI classified as {category} with {priority} priority and {sentiment} sentiment."
    )
    return {
        "ai_category": category,
        "ai_priority": priority,
        "ai_sentiment": sentiment,
        "ai_confidence": None,
        "ai_explanation": explanation,
    }
