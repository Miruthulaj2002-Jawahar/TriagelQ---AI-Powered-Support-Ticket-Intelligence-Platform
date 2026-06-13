from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_database
from app.schemas.ticket import (
    TicketCreate,
    TicketPriority,
    TicketResponse,
    TicketSentiment,
    TicketStatus,
    TicketUpdate,
)
from app.schemas.user import UserResponse, UserRole
from app.services.classifier import classify_ticket
from app.services.security import get_current_user, require_admin

router = APIRouter(prefix="/tickets", tags=["tickets"])


def parse_ticket_id(ticket_id: str) -> ObjectId:
    try:
        return ObjectId(ticket_id)
    except InvalidId as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ticket ID",
        ) from exc


def ticket_doc_to_response(ticket: dict[str, Any]) -> TicketResponse:
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
    )


def ensure_ticket_access(ticket: dict[str, Any], current_user: UserResponse) -> None:
    if current_user.role == UserRole.ADMIN:
        return

    if ticket.get("assigned_agent_id") != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this ticket",
        )


async def get_accessible_ticket(
    ticket_id: str,
    db: AsyncIOMotorDatabase,
    current_user: UserResponse,
) -> dict[str, Any]:
    ticket = await db.tickets.find_one({"_id": parse_ticket_id(ticket_id)})
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    ensure_ticket_access(ticket, current_user)
    return ticket


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserResponse = Depends(get_current_user),
) -> TicketResponse:
    classification = classify_ticket(payload.title, payload.description)

    category = payload.category or classification["category"]
    priority = payload.priority.value if payload.priority else classification["priority"]
    sentiment = payload.sentiment.value if payload.sentiment else classification["sentiment"]
    assigned_queue = payload.assigned_queue or classification["assigned_queue"]

    assigned_agent_id = payload.assigned_agent_id
    if assigned_agent_id is None and current_user.role == UserRole.AGENT:
        assigned_agent_id = current_user.id

    now = datetime.now(UTC)
    ticket_doc = {
        "title": payload.title,
        "description": payload.description,
        "customer_email": str(payload.customer_email).lower(),
        "status": TicketStatus.OPEN.value,
        "category": category,
        "priority": priority,
        "sentiment": sentiment,
        "assigned_queue": assigned_queue,
        "assigned_agent_id": assigned_agent_id,
        "created_by": current_user.id,
        "created_at": now,
        "updated_at": now,
    }

    result = await db.tickets.insert_one(ticket_doc)
    created = await db.tickets.find_one({"_id": result.inserted_id})
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create ticket",
        )

    return ticket_doc_to_response(created)


@router.get("", response_model=list[TicketResponse])
async def list_tickets(
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserResponse = Depends(get_current_user),
) -> list[TicketResponse]:
    tickets = await db.tickets.find().sort("created_at", -1).to_list(length=None)
    return [ticket_doc_to_response(ticket) for ticket in tickets]


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserResponse = Depends(get_current_user),
) -> TicketResponse:
    ticket = await get_accessible_ticket(ticket_id, db, current_user)
    return ticket_doc_to_response(ticket)


@router.put("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    payload: TicketUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserResponse = Depends(get_current_user),
) -> TicketResponse:
    object_id = parse_ticket_id(ticket_id)
    ticket = await db.tickets.find_one({"_id": object_id})
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    ensure_ticket_access(ticket, current_user)

    update_data = payload.model_dump(exclude_unset=True)

    if current_user.role != UserRole.ADMIN and "assigned_agent_id" in update_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can reassign tickets",
        )

    if "customer_email" in update_data and update_data["customer_email"] is not None:
        update_data["customer_email"] = str(update_data["customer_email"]).lower()

    for field in ("status", "priority", "sentiment"):
        if field in update_data and update_data[field] is not None:
            update_data[field] = update_data[field].value

    update_data["updated_at"] = datetime.now(UTC)

    result = await db.tickets.update_one({"_id": object_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    updated = await db.tickets.find_one({"_id": object_id})
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    return ticket_doc_to_response(updated)


@router.delete("/{ticket_id}")
async def delete_ticket(
    ticket_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserResponse = Depends(require_admin),
) -> dict[str, str]:
    result = await db.tickets.delete_one({"_id": parse_ticket_id(ticket_id)})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    return {"message": "Ticket deleted successfully"}
