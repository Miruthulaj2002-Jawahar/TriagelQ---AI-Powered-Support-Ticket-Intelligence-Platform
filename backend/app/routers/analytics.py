from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.db.mongodb import get_database
from app.schemas.ticket import TicketPriority, TicketSentiment, TicketStatus
from app.schemas.user import UserResponse
from app.services.security import require_admin

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
    overridden_tickets: int
    ai_accuracy: float
    tickets_by_status: dict[str, int]
    tickets_by_priority: dict[str, int]
    tickets_by_category: dict[str, int]
    tickets_by_sentiment: dict[str, int]
    resolution_rate: float


OVERRIDDEN_TICKET_FILTER = {
    "$or": [
        {"category_override": {"$exists": True, "$ne": None}},
        {"priority_override": {"$exists": True, "$ne": None}},
        {"overridden_at": {"$exists": True, "$ne": None}},
    ]
}


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

    overridden_tickets = await db.tickets.count_documents(OVERRIDDEN_TICKET_FILTER)
    not_overridden = max(total_tickets - overridden_tickets, 0)
    ai_accuracy = round((not_overridden / total_tickets) * 100, 2) if total_tickets else 0.0

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
        overridden_tickets=overridden_tickets,
        ai_accuracy=ai_accuracy,
        tickets_by_status=tickets_by_status,
        tickets_by_priority=tickets_by_priority,
        tickets_by_category=tickets_by_category,
        tickets_by_sentiment=tickets_by_sentiment,
        resolution_rate=resolution_rate,
    )
