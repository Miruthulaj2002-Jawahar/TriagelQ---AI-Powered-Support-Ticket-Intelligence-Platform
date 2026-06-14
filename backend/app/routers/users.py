from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.db.mongodb import get_database
from app.schemas.user import (
    UserCreate,
    UserCreateResponse,
    UserListResponse,
    UserResponse,
    UserRole,
)
from app.services.security import hash_password, require_admin

router = APIRouter(prefix="/users", tags=["users"])


def user_doc_to_list_response(user: dict[str, Any]) -> UserListResponse:
    return UserListResponse(
        id=str(user["_id"]),
        full_name=user["full_name"],
        email=user["email"],
        role=UserRole(user["role"]),
        created_at=user["created_at"],
    )


def user_doc_to_create_response(user: dict[str, Any]) -> UserCreateResponse:
    return UserCreateResponse(
        id=str(user["_id"]),
        name=user["full_name"],
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


@router.post("", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserResponse = Depends(require_admin),
) -> UserCreateResponse:
    user_doc = {
        "full_name": payload.name.strip(),
        "email": str(payload.email).lower(),
        "role": payload.role.value,
        "hashed_password": hash_password(payload.password),
        "is_active": True,
        "created_at": datetime.now(UTC),
    }

    try:
        result = await db.users.insert_one(user_doc)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from exc

    created = await db.users.find_one({"_id": result.inserted_id})
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )

    return user_doc_to_create_response(created)
