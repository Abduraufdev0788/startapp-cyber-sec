"""
Authentication and User Account Endpoints.
Handles registration, login, JWT issuance (access & refresh tokens), and profile retrieval.
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AppException, AuthenticationException
from app.core.rate_limit import rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db_session
from app.modules.audit.service import AuditService
from app.modules.users.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    """User registration payload."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Kamida 8 ta belgidan iborat parol")


class LoginRequest(BaseModel):
    """User login payload."""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token payload."""
    refresh_token: str


class AuthTokenResponse(BaseModel):
    """Token response payload."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    user_id: str
    email: str
    role: str


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(times=10, seconds=60, key_prefix="rl_reg"))],
)
async def register(
    payload: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
) -> dict[str, Any]:
    """Registers a new user on the platform."""
    clean_email = payload.email.lower().strip()

    # Check if user already exists
    stmt = select(User).where(User.email == clean_email)
    existing = await db.execute(stmt)
    if existing.scalar_one_or_none():
        raise AppException(
            message="Ushbu elektron pochta allaqachon ro'yxatdan o'tgan.",
            code="EMAIL_ALREADY_EXISTS",
            status_code=status.HTTP_409_CONFLICT,
        )

    # Hash password with Argon2id
    hashed = hash_password(payload.password)
    user = User(
        id=uuid.uuid4(),
        email=clean_email,
        hashed_password=hashed,
        role="USER",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    await AuditService.log_event(
        db=db,
        action="USER_REGISTER",
        user_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
        details={"email": user.email, "role": user.role},
    )

    access_token = create_access_token(subject=str(user.id), role=user.role)
    refresh_token = create_refresh_token(subject=str(user.id), role=user.role)

    return {
        "success": True,
        "data": {
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        },
        "message": "Foydalanuvchi muvaffaqiyatli ro'yxatdan o'tkazildi.",
    }


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit(times=15, seconds=60, key_prefix="rl_login"))],
)
async def login(
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
) -> dict[str, Any]:
    """Authenticates a user and issues access and refresh JWT tokens."""
    clean_email = payload.email.lower().strip()
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    stmt = select(User).where(User.email == clean_email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        await AuditService.log_event(
            db=db,
            action="LOGIN_FAILED",
            user_id=user.id if user else None,
            ip_address=client_ip,
            user_agent=user_agent,
            details={"email": clean_email, "reason": "INVALID_CREDENTIALS"},
        )
        raise AuthenticationException(
            message="Elektron pochta yoki parol noto'g'ri.",
            code="INVALID_CREDENTIALS",
        )

    if not user.is_active:
        await AuditService.log_event(
            db=db,
            action="LOGIN_FAILED",
            user_id=user.id,
            ip_address=client_ip,
            user_agent=user_agent,
            details={"email": clean_email, "reason": "ACCOUNT_DISABLED"},
        )
        raise AuthenticationException(
            message="Akkaunt faol emas. Iltimos, ma'muriyat bilan bog'laning.",
            code="ACCOUNT_DISABLED",
        )

    access_token = create_access_token(subject=str(user.id), role=user.role)
    refresh_token = create_refresh_token(subject=str(user.id), role=user.role)

    await AuditService.log_event(
        db=db,
        action="USER_LOGIN",
        user_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
        details={"email": user.email},
    )

    return {
        "success": True,
        "data": {
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        },
    }


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_tokens(
    payload: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
) -> dict[str, Any]:
    """Validates refresh token and generates a fresh access/refresh token pair."""
    token_claims = decode_refresh_token(payload.refresh_token)
    user_id_str = token_claims.get("sub")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except (ValueError, TypeError) as err:
        raise AuthenticationException("Invalid user ID in token.", code="INVALID_TOKEN") from err

    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise AuthenticationException(
            message="Foydalanuvchi topilmadi yoki hisob faol emas.",
            code="INVALID_REFRESH_TOKEN",
        )

    access_token = create_access_token(subject=str(user.id), role=user.role)
    refresh_token = create_refresh_token(subject=str(user.id), role=user.role)

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    await AuditService.log_event(
        db=db,
        action="TOKEN_REFRESH",
        user_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
        details={"email": user.email},
    )

    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        },
    }


@router.get("/me", status_code=status.HTTP_200_OK)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """Returns the profile of the currently authenticated user."""
    return {
        "success": True,
        "data": {
            "user_id": str(current_user.id),
            "email": current_user.email,
            "role": current_user.role,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        },
    }
