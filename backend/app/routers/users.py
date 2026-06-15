from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from app.db.mongodb import get_database
from app.schemas.user import (
    AgentSummaryResponse,
    UserCreate,
    UserCreateResponse,
    UserListResponse,
    UserResponse,
    UserRole,
)
from app.services.security import hash_password, require_admin

router = APIRouter(prefix="/users", tags=["users"])


def parse_user_id(user_id: str) -> ObjectId:
    try:
        return ObjectId(user_id)
    except InvalidId as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        ) from exc


def user_doc_to_list_response(user: dict[str, Any]) -> UserListResponse:
    return UserListResponse(
        id=str(user["_id"]),
        full_name=user["full_name"],
        email=user["email"],
        role=UserRole(user["role"]),
        is_active=user.get("is_active", True),
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


async def count_active_admins(db: AsyncIOMotorDatabase) -> int:
    return await db.users.count_documents(
        {
            "role": UserRole.ADMIN.value,
            "$or": [{"is_active": True}, {"is_active": {"$exists": False}}],
        }
    )


async def ensure_user_can_be_deactivated(
    target_user: dict[str, Any],
    current_user: UserResponse,
    db: AsyncIOMotorDatabase,
) -> None:
    target_id = str(target_user["_id"])

    if target_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )

    if not target_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already inactive",
        )

    if target_user["role"] == UserRole.ADMIN.value:
        active_admin_count = await count_active_admins(db)
        if active_admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last active admin",
            )


@router.get(
    "/agents",
    response_model=list[AgentSummaryResponse],
    summary="List active agents",
    operation_id="list_agents",
)
async def list_agents(
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserResponse = Depends(require_admin),
) -> list[AgentSummaryResponse]:
    agents = await db.users.find(
        {
            "role": UserRole.AGENT.value,
            "$or": [{"is_active": True}, {"is_active": {"$exists": False}}],
        }
    ).sort("full_name", 1).to_list(length=None)

    return [
        AgentSummaryResponse(
            id=str(agent["_id"]),
            email=agent["email"],
            name=agent["full_name"],
            role=UserRole(agent["role"]),
        )
        for agent in agents
    ]


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


@router.delete("/{user_id}", response_model=UserListResponse)
async def deactivate_user(
    user_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: UserResponse = Depends(require_admin),
) -> UserListResponse:
    object_id = parse_user_id(user_id)
    target_user = await db.users.find_one({"_id": object_id})
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await ensure_user_can_be_deactivated(target_user, current_user, db)

    await db.users.update_one({"_id": object_id}, {"$set": {"is_active": False}})

    updated = await db.users.find_one({"_id": object_id})
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user_doc_to_list_response(updated)
