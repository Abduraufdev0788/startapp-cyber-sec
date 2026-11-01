"""
Telegram Account Management API Endpoints.
Handles sending verification codes, verifying OTP/2FA, listing accounts/chats, and disconnecting accounts.
Enforces tenant isolation (IDOR mitigation) through get_current_user.
"""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import ResourceNotFoundException
from app.core.rate_limit import rate_limit
from app.db.session import get_db_session
from app.modules.audit.service import AuditService
from app.modules.telegram_accounts.models import TelegramAccount
from app.modules.telegram_accounts.service import TelegramAccountService
from app.modules.users.models import User

router = APIRouter(prefix="/telegram", tags=["Telegram Accounts"])


class SendCodeRequest(BaseModel):
    phone_number: str = Field(..., description="Telefon raqami (masalan: +998901234567)")


class VerifyCodeRequest(BaseModel):
    phone_number: str
    phone_code_hash: str
    code: str = Field(..., description="Telegram ilovasiga yuborilgan 5 xonali kod")


class Verify2FARequest(BaseModel):
    phone_number: str
    password: str = Field(..., description="Telegram 2FA bulutli paroli")


@router.post(
    "/auth/send-code",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit(times=5, seconds=60, key_prefix="rl_tg_send"))],
)
async def send_code_endpoint(
    payload: SendCodeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """Sends a Telegram verification code to the provided phone number."""
    result = await TelegramAccountService.send_code(payload.phone_number)
    return {
        "success": True,
        "data": result,
    }


@router.post(
    "/auth/verify-code",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit(times=10, seconds=60, key_prefix="rl_tg_verify"))],
)
async def verify_code_endpoint(
    payload: VerifyCodeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Verifies the Telegram OTP code and binds account to the authenticated user."""
    result = await TelegramAccountService.verify_code(
        user_id=current_user.id,
        phone_number=payload.phone_number,
        phone_code_hash=payload.phone_code_hash,
        code=payload.code,
    )
    if result.get("status") == "CONNECTED":
        await AuditService.log_event(
            db=db,
            action="ACCOUNT_CONNECT",
            user_id=current_user.id,
            details={"telegram_user_id": result.get("telegram_user_id")},
        )
    return {
        "success": True,
        "data": result,
    }


@router.post("/auth/verify-2fa", status_code=status.HTTP_200_OK)
async def verify_2fa_endpoint(
    payload: Verify2FARequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Verifies the 2FA cloud password if enabled on the Telegram account."""
    result = await TelegramAccountService.verify_2fa(
        user_id=current_user.id,
        phone_number=payload.phone_number,
        password_2fa=payload.password,
    )
    if result.get("status") == "CONNECTED":
        await AuditService.log_event(
            db=db,
            action="ACCOUNT_CONNECT",
            user_id=current_user.id,
            details={"telegram_user_id": result.get("telegram_user_id")},
        )
    return {
        "success": True,
        "data": result,
    }


@router.get("/accounts", status_code=status.HTTP_200_OK)
async def get_accounts_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Lists connected Telegram accounts belonging strictly to the authenticated user."""
    stmt = (
        select(TelegramAccount)
        .where(TelegramAccount.user_id == current_user.id)
        .order_by(TelegramAccount.created_at.desc())
    )
    result = await db.execute(stmt)
    accounts = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "account_id": str(acc.id),
                "telegram_user_id": acc.telegram_user_id,
                "status": acc.status,
                "auth_state": acc.auth_state,
                "last_connected_at": acc.last_connected_at.isoformat() if acc.last_connected_at else None,
                "created_at": acc.created_at.isoformat() if acc.created_at else None,
            }
            for acc in accounts
        ],
    }


@router.get("/accounts/{account_id}/chats", status_code=status.HTTP_200_OK)
async def get_account_chats_endpoint(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Lists monitored chats for an account owned by the authenticated user."""
    chats = await TelegramAccountService.get_account_chats(
        account_id=account_id,
        user_id=current_user.id,
        db=db,
    )
    return {
        "success": True,
        "count": len(chats),
        "data": chats,
    }


@router.delete("/accounts/{account_id}", status_code=status.HTTP_200_OK)
async def disconnect_account_endpoint(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """
    Disconnects a Telegram account:
    Officially revokes the Telethon session on Telegram servers and removes DB records.
    Enforces tenant ownership check (Anti-IDOR).
    """
    stmt = select(TelegramAccount).where(
        TelegramAccount.id == account_id,
        TelegramAccount.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise ResourceNotFoundException("Telegram hisobi topilmadi.")

    tg_uid = account.telegram_user_id
    await TelegramAccountService.disconnect_account(
        account=account,
        user_id=current_user.id,
        db=db,
    )

    await AuditService.log_event(
        db=db,
        action="ACCOUNT_DISCONNECT",
        user_id=current_user.id,
        details={"account_id": str(account_id), "telegram_user_id": tg_uid},
    )

    return {
        "success": True,
        "message": "Telegram hisobi muvaffaqiyatli uzildi va seans serverdan bekor qilindi.",
    }


@router.post("/accounts/{account_id}/sync-chats", status_code=status.HTTP_200_OK)
async def sync_account_chats_endpoint(
    account_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Manually triggers chat discovery and synchronization for the user's account."""
    stmt = select(TelegramAccount).where(
        TelegramAccount.id == account_id,
        TelegramAccount.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise ResourceNotFoundException("Telegram hisobi topilmadi.")

    synced_count = await TelegramAccountService.refresh_account_chats(
        account=account,
        user_id=current_user.id,
        db=db,
    )

    await AuditService.log_event(
        db=db,
        action="SYNC_CHATS",
        user_id=current_user.id,
        details={"account_id": str(account_id), "synced_count": synced_count},
    )

    return {
        "success": True,
        "message": f"{synced_count} ta guruh va kanal muvaffaqiyatli sinxronlashtirildi.",
        "synced_count": synced_count,
    }

