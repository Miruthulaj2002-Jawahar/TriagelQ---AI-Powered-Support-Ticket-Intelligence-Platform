from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_database
from app.schemas.ticket import (
    ALLOWED_TICKET_CATEGORIES,
    TicketCreate,
    TicketOverrideRequest,
    TicketResponse,
    TicketStatus,
    TicketUpdate,
)
from app.schemas.user import UserResponse, UserRole
from app.services.assignment import resolve_agent_assignment
from app.services.classifier import classify_ticket
from app.services.security import get_current_user, require_admin, require_agent_or_admin
from app.services.ticket_mapping import (
    build_ai_storage_fields,
    compute_effective_category,
    compute_effective_priority,
    resolve_ai_fields,
    ticket_doc_to_response,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])

OVERRIDE_CLEAR_FIELDS = {
    "category_override": None,
    "priority_override": None,
    "override_reason": None,
    "overridden_by": None,
    "overridden_at": None,
}


def parse_ticket_id(ticket_id: str) -> ObjectId:
    try:
        return ObjectId(ticket_id)
    except InvalidId as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ticket ID",
        ) from exc


def get_ticket_list_filter(current_user: UserResponse) -> dict[str, Any]:
    if current_user.role == UserRole.ADMIN:
        return {}
    return {"assigned_agent_id": current_user.id}


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


async def enrich_ticket_response(
    db: AsyncIOMotorDatabase,
    ticket: dict[str, Any],
) -> TicketResponse:
    overridden_by_name = None
    overridden_by_email = None
    overridden_by_id = ticket.get("overridden_by")

    if overridden_by_id:
        try:
            user = await db.users.find_one({"_id": ObjectId(overridden_by_id)})
        except InvalidId:
            user = None
        if user:
            overridden_by_name = user.get("full_name")
            overridden_by_email = user.get("email")

    assigned_agent_email = ticket.get("assigned_agent_email")
    assigned_agent_name = None
    assigned_agent_id = ticket.get("assigned_agent_id")

    if assigned_agent_id and not assigned_agent_email:
        try:
            agent = await db.users.find_one({"_id": ObjectId(assigned_agent_id)})
        except InvalidId:
            agent = None
        if agent:
            assigned_agent_email = agent.get("email")
            assigned_agent_name = agent.get("full_name")
    elif assigned_agent_id:
        try:
            agent = await db.users.find_one({"_id": ObjectId(assigned_agent_id)})
        except InvalidId:
            agent = None
        if agent:
            assigned_agent_name = agent.get("full_name")

    return ticket_doc_to_response(
        ticket,
        overridden_by_name=overridden_by_name,
        overridden_by_email=overridden_by_email,
        assigned_agent_email=assigned_agent_email,
        assigned_agent_name=assigned_agent_name,
    )


def resolve_assigned_agent_id_on_create(
    payload: TicketCreate,
    current_user: UserResponse,
) -> str | None:
    if current_user.role == UserRole.AGENT:
        if payload.assigned_agent_id and payload.assigned_agent_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Agents cannot assign tickets to other users",
            )
        return current_user.id

    return payload.assigned_agent_id


def validate_override_category(category: str) -> str:
    normalized = category.strip()
    if normalized not in ALLOWED_TICKET_CATEGORIES:
        allowed = ", ".join(ALLOWED_TICKET_CATEGORIES)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category. Allowed values: {allowed}",
        )
    return normalized


def build_override_update(
    ticket: dict[str, Any],
    payload: TicketOverrideRequest,
    current_user: UserResponse,
) -> dict[str, Any]:
    ai_fields = resolve_ai_fields(ticket)
    ai_category = ai_fields["ai_category"]
    ai_priority = ai_fields["ai_priority"]

    selected_category = validate_override_category(payload.category)
    selected_priority = payload.priority.value

    category_differs = selected_category != ai_category
    priority_differs = selected_priority != ai_priority

    if not category_differs and not priority_differs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected values match AI classification; no override applied",
        )

    update_data: dict[str, Any] = {
        "updated_at": datetime.now(UTC),
        "overridden_by": current_user.id,
        "overridden_at": datetime.now(UTC),
        "override_reason": payload.override_reason.strip() if payload.override_reason else None,
    }

    if category_differs:
        update_data["category_override"] = selected_category
    else:
        update_data["category_override"] = None

    if priority_differs:
        update_data["priority_override"] = selected_priority
    else:
        update_data["priority_override"] = None

    preview_ticket = {**ticket, **update_data}
    update_data["category"] = compute_effective_category(preview_ticket, ai_fields)
    update_data["priority"] = compute_effective_priority(preview_ticket, ai_fields)

    return update_data


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

    assigned_agent_id = resolve_assigned_agent_id_on_create(payload, current_user)
    assigned_agent_id, assigned_agent_email = await resolve_agent_assignment(
        db,
        assigned_agent_id,
    )

    now = datetime.now(UTC)
    ai_fields = build_ai_storage_fields(
        classification["category"],
        classification["priority"],
        classification["sentiment"],
        confidence=classification.get("confidence"),
        explanation=classification.get("explanation"),
    )
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
        "assigned_agent_email": assigned_agent_email,
        "created_by": current_user.id,
        "created_at": now,
        "updated_at": now,
        **ai_fields,
    }

    result = await db.tickets.insert_one(ticket_doc)
    created = await db.tickets.find_one({"_id": result.inserted_id})
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create ticket",
        )

    return await enrich_ticket_response(db, created)


@router.get("", response_model=list[TicketResponse])
async def list_tickets(
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserResponse = Depends(get_current_user),
) -> list[TicketResponse]:
    ticket_filter = get_ticket_list_filter(current_user)
    tickets = await db.tickets.find(ticket_filter).sort("created_at", -1).to_list(length=None)
    return [await enrich_ticket_response(db, ticket) for ticket in tickets]


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserResponse = Depends(get_current_user),
) -> TicketResponse:
    ticket = await get_accessible_ticket(ticket_id, db, current_user)
    return await enrich_ticket_response(db, ticket)


@router.patch("/{ticket_id}/override", response_model=TicketResponse)
async def override_ticket_classification(
    ticket_id: str,
    payload: TicketOverrideRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserResponse = Depends(require_agent_or_admin),
) -> TicketResponse:
    object_id = parse_ticket_id(ticket_id)
    ticket = await get_accessible_ticket(ticket_id, db, current_user)
    update_data = build_override_update(ticket, payload, current_user)

    await db.tickets.update_one({"_id": object_id}, {"$set": update_data})

    updated = await db.tickets.find_one({"_id": object_id})
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    return await enrich_ticket_response(db, updated)


@router.delete("/{ticket_id}/override", response_model=TicketResponse)
async def reset_ticket_override(
    ticket_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserResponse = Depends(require_agent_or_admin),
) -> TicketResponse:
    object_id = parse_ticket_id(ticket_id)
    ticket = await get_accessible_ticket(ticket_id, db, current_user)
    ai_fields = resolve_ai_fields(ticket)

    update_data = {
        **OVERRIDE_CLEAR_FIELDS,
        "category": ai_fields["ai_category"],
        "priority": ai_fields["ai_priority"],
        "updated_at": datetime.now(UTC),
    }

    await db.tickets.update_one({"_id": object_id}, {"$set": update_data})

    updated = await db.tickets.find_one({"_id": object_id})
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    return await enrich_ticket_response(db, updated)


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

    if current_user.role != UserRole.ADMIN:
        disallowed_fields = set(update_data.keys()) - {"status"}
        if disallowed_fields:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Agents can only update ticket status",
            )

    if "assigned_agent_id" in update_data:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can assign or reassign tickets",
            )
        resolved_id, resolved_email = await resolve_agent_assignment(
            db,
            update_data["assigned_agent_id"],
        )
        update_data["assigned_agent_id"] = resolved_id
        update_data["assigned_agent_email"] = resolved_email

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

    return await enrich_ticket_response(db, updated)


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
