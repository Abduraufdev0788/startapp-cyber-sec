"""
FastAPI Request Dependencies.
Provides authenticated user context via Bearer JWT, Redis connection, and role checks.
"""

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationException, ForbiddenException
from app.core.security import decode_access_token
from app.db.session import get_db_session
from app.modules.users.models import User

security_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_bearer)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """
    Validates the Bearer access token and resolves the corresponding User entity.
    Raises AuthenticationException if token is missing, expired, invalid, or user is inactive.
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    sub = payload.get("sub")
    if not sub:
        raise AuthenticationException("Token claim 'sub' is missing.", code="INVALID_TOKEN")

    try:
        user_uuid = uuid.UUID(sub)
    except (ValueError, TypeError) as err:
        raise AuthenticationException("Invalid user ID format in token.", code="INVALID_TOKEN") from err

    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationException("User account not found.", code="USER_NOT_FOUND")

    if not user.is_active:
        raise ForbiddenException("User account is disabled or deactivated.")

    return user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Ensures the authenticated user has ADMIN role."""
    if current_user.role != "ADMIN":
        raise ForbiddenException("Administrator privileges required.")
    return current_user
