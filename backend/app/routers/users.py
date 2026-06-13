from typing import Any

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_database
from app.schemas.user import UserListResponse, UserResponse, UserRole
from app.services.security import require_admin

router = APIRouter(prefix="/users", tags=["users"])


def user_doc_to_list_response(user: dict[str, Any]) -> UserListResponse:
    return UserListResponse(
        id=str(user["_id"]),
        full_name=user["full_name"],
        email=user["email"],
        role=UserRole(user["role"]),
        created_at=user["created_at"],
    )


@router.get("", response_model=list[UserListResponse])
async def list_users(
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserResponse = Depends(require_admin),
) -> list[UserListResponse]:
    users = await db.users.find().sort("created_at", -1).to_list(length=None)
    return [user_doc_to_list_response(user) for user in users]
