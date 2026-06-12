from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from bson.errors import InvalidId
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorDatabase
from passlib.context import CryptContext

from app.core.config import settings
from app.db.mongodb import get_database
from app.schemas.user import UserResponse, UserRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, settings.jwt_algorithm)


def user_doc_to_response(user: dict[str, Any]) -> UserResponse:
    return UserResponse(
        id=str(user["_id"]),
        full_name=user["full_name"],
        email=user["email"],
        role=UserRole(user["role"]),
        is_active=user["is_active"],
        created_at=user["created_at"],
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> UserResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    from bson import ObjectId

    try:
        object_id = ObjectId(user_id)
    except InvalidId as exc:
        raise credentials_exception from exc

    user = await db.users.find_one({"_id": object_id})
    if user is None:
        raise credentials_exception

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    return user_doc_to_response(user)


def require_roles(*allowed_roles: UserRole) -> Callable:
    async def role_checker(
        current_user: UserResponse = Depends(get_current_user),
    ) -> UserResponse:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return role_checker


async def require_admin(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def require_agent_or_admin(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    if current_user.role not in (UserRole.ADMIN, UserRole.AGENT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent or admin access required",
        )
    return current_user
