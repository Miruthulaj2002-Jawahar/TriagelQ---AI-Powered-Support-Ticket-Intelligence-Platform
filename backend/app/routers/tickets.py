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
from app.schemas.user import UserResponse
from app.services.security import get_current_user

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
        created_by=ticket["created_by"],
        created_at=ticket["created_at"],
        updated_at=ticket["updated_at"],
    )


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserResponse = Depends(get_current_user),
) -> TicketResponse:
    now = datetime.now(UTC)
    ticket_doc = {
        "title": payload.title,
        "description": payload.description,
        "customer_email": str(payload.customer_email).lower(),
        "status": TicketStatus.OPEN.value,
        "category": payload.category,
        "priority": payload.priority.value,
        "sentiment": payload.sentiment.value,
        "assigned_queue": payload.assigned_queue,
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
    ticket = await db.tickets.find_one({"_id": parse_ticket_id(ticket_id)})
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    return ticket_doc_to_response(ticket)


@router.put("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    payload: TicketUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserResponse = Depends(get_current_user),
) -> TicketResponse:
    object_id = parse_ticket_id(ticket_id)
    update_data = payload.model_dump(exclude_unset=True)

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
    current_user: UserResponse = Depends(get_current_user),
) -> dict[str, str]:
    result = await db.tickets.delete_one({"_id": parse_ticket_id(ticket_id)})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    return {"message": "Ticket deleted successfully"}
