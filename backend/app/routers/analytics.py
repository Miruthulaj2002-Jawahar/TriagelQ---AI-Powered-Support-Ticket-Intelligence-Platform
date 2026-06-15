from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.db.mongodb import get_database
from app.schemas.ticket import TicketPriority, TicketSentiment, TicketStatus
from app.schemas.user import UserResponse
from app.services.security import require_admin
from app.services.ticket_mapping import compute_ai_accuracy_metrics

router = APIRouter(prefix="/analytics", tags=["analytics"])


class AnalyticsSummary(BaseModel):
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    resolved_tickets: int
    closed_tickets: int
    urgent_tickets: int
    high_priority_tickets: int
    negative_sentiment_tickets: int
    total_classified_tickets: int
    overridden_ticket_count: int
    accepted_ai_count: int
    override_rate: float
    ai_accuracy: float
    ai_classification_summary: dict[str, int]
    overridden_tickets: int
    tickets_by_status: dict[str, int]
    tickets_by_priority: dict[str, int]
    tickets_by_category: dict[str, int]
    tickets_by_sentiment: dict[str, int]
    resolution_rate: float


async def count_by_field(
    db: AsyncIOMotorDatabase,
    field: str,
    default_label: str = "Unknown",
) -> dict[str, int]:
    pipeline = [
        {
            "$group": {
                "_id": {"$ifNull": [f"${field}", default_label]},
                "count": {"$sum": 1},
            }
        }
    ]
    results = await db.tickets.aggregate(pipeline).to_list(length=None)
    return {str(item["_id"]): item["count"] for item in results}


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserResponse = Depends(require_admin),
) -> AnalyticsSummary:
    total_tickets = await db.tickets.count_documents({})

    open_tickets = await db.tickets.count_documents({"status": TicketStatus.OPEN.value})
    in_progress_tickets = await db.tickets.count_documents(
        {"status": TicketStatus.IN_PROGRESS.value}
    )
    resolved_tickets = await db.tickets.count_documents({"status": TicketStatus.RESOLVED.value})
    closed_tickets = await db.tickets.count_documents({"status": TicketStatus.CLOSED.value})

    urgent_tickets = await db.tickets.count_documents({"priority": TicketPriority.URGENT.value})
    high_priority_tickets = await db.tickets.count_documents({"priority": TicketPriority.HIGH.value})
    negative_sentiment_tickets = await db.tickets.count_documents(
        {"sentiment": TicketSentiment.NEGATIVE.value}
    )

    tickets_by_status = await count_by_field(db, "status")
    tickets_by_priority = await count_by_field(db, "priority")
    tickets_by_category = await count_by_field(db, "category")
    tickets_by_sentiment = await count_by_field(db, "sentiment")

    all_tickets = await db.tickets.find().to_list(length=None)
    ai_metrics = compute_ai_accuracy_metrics(all_tickets)

    resolved_count = resolved_tickets + closed_tickets
    resolution_rate = round((resolved_count / total_tickets) * 100, 2) if total_tickets else 0.0

    return AnalyticsSummary(
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        in_progress_tickets=in_progress_tickets,
        resolved_tickets=resolved_tickets,
        closed_tickets=closed_tickets,
        urgent_tickets=urgent_tickets,
        high_priority_tickets=high_priority_tickets,
        negative_sentiment_tickets=negative_sentiment_tickets,
        total_classified_tickets=int(ai_metrics["total_classified_tickets"]),
        overridden_ticket_count=int(ai_metrics["overridden_ticket_count"]),
        accepted_ai_count=int(ai_metrics["accepted_ai_count"]),
        override_rate=float(ai_metrics["override_rate"]),
        ai_accuracy=float(ai_metrics["ai_accuracy"]),
        ai_classification_summary=dict(ai_metrics["ai_classification_summary"]),
        overridden_tickets=int(ai_metrics["overridden_ticket_count"]),
        tickets_by_status=tickets_by_status,
        tickets_by_priority=tickets_by_priority,
        tickets_by_category=tickets_by_category,
        tickets_by_sentiment=tickets_by_sentiment,
        resolution_rate=resolution_rate,
    )
