"""Ticket assignment helpers."""

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.user import UserRole


async def resolve_agent_assignment(
    db: AsyncIOMotorDatabase,
    assigned_agent_id: str | None,
) -> tuple[str | None, str | None]:
    """Validate agent id and return (assigned_agent_id, assigned_agent_email)."""
    if not assigned_agent_id:
        return None, None

    try:
        object_id = ObjectId(assigned_agent_id)
    except InvalidId as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agent ID",
        ) from exc

    agent = await db.users.find_one({"_id": object_id})
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned agent not found",
        )

    if agent.get("role") != UserRole.AGENT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tickets can only be assigned to users with the AGENT role",
        )

    if not agent.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign tickets to inactive agents",
        )

    return str(agent["_id"]), agent["email"]
