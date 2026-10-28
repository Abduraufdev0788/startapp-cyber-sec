"""
Unit and integration tests for Telegram Account Management API endpoints (/api/v1/telegram).
Verifies authentication flows, anti-IDOR tenant isolation, chat listing, and disconnect lifecycle.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.main import app
from app.modules.telegram_accounts.models import TelegramAccount
from app.modules.users.models import User


@pytest.fixture
def test_user():
    return User(
        id=uuid.uuid4(),
        email="test_tg_user@phishguard.uz",
        hashed_password="hashed_pw",
        role="USER",
        is_active=True,
    )


@pytest.fixture
def other_user():
    return User(
        id=uuid.uuid4(),
        email="other_tg_user@phishguard.uz",
        hashed_password="hashed_pw",
        role="USER",
        is_active=True,
    )


@pytest.mark.asyncio
async def test_send_code_endpoint(test_user):
    """Verifies POST /api/v1/telegram/auth/send-code triggers send_code."""
    app.dependency_overrides[get_current_user] = lambda: test_user

    with patch(
        "app.modules.telegram_accounts.service.TelegramAccountService.send_code",
        new=AsyncMock(return_value={
            "phone_number": "+998901234567",
            "phone_code_hash": "mock_hash_123",
            "status": "CODE_SENT",
            "message": "Tasdiqlash kodi Telegram ilovangizga yuborildi.",
        }),
    ):
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/telegram/auth/send-code",
                    json={"phone_number": "+998901234567"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["success"] is True
                assert data["data"]["phone_code_hash"] == "mock_hash_123"
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_verify_code_endpoint(test_user):
    """Verifies POST /api/v1/telegram/auth/verify-code connects account and logs audit."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    mock_db = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_db

    mock_return = {
        "account_id": str(uuid.uuid4()),
        "telegram_user_id": 999888777,
        "first_name": "Alisher",
        "username": "alisher_dev",
        "status": "CONNECTED",
        "message": "Hisob ulandi.",
    }

    with patch(
        "app.modules.telegram_accounts.service.TelegramAccountService.verify_code",
        new=AsyncMock(return_value=mock_return),
    ), patch("app.modules.audit.service.AuditService.log_event", new=AsyncMock()) as mock_audit:
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/telegram/auth/verify-code",
                    json={
                        "phone_number": "+998901234567",
                        "phone_code_hash": "mock_hash_123",
                        "code": "12345",
                    },
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["success"] is True
                assert data["data"]["status"] == "CONNECTED"
                assert mock_audit.await_count == 1
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_accounts_endpoint(test_user):
    """Verifies GET /api/v1/telegram/accounts returns only current user's accounts."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    mock_db = AsyncMock()

    acc1 = TelegramAccount(
        id=uuid.uuid4(),
        user_id=test_user.id,
        telegram_user_id=111222,
        encrypted_session=b"dummy",
        status="CONNECTED",
        auth_state="AUTHORIZED",
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [acc1]
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db_session] = lambda: mock_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/telegram/accounts")
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert len(data["data"]) == 1
            assert data["data"][0]["telegram_user_id"] == 111222
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_anti_idor_disconnect_other_user_account(test_user, other_user):
    """Verifies that user A cannot disconnect user B's account (Anti-IDOR)."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    mock_db = AsyncMock()

    # Query searching for account with account_id AND user_id == test_user.id returns None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db_session] = lambda: mock_db

    victim_account_id = uuid.uuid4()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete(f"/api/v1/telegram/accounts/{victim_account_id}")
            # Must return 404 Not Found since it does not belong to test_user
            assert resp.status_code == 404
            assert "topilmadi" in resp.json()["error"]["message"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_disconnect_own_account_success(test_user):
    """Verifies disconnecting own account logs out and deletes."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    mock_db = AsyncMock()

    own_account_id = uuid.uuid4()
    account = TelegramAccount(
        id=own_account_id,
        user_id=test_user.id,
        telegram_user_id=555444,
        encrypted_session=b"dummy",
        status="CONNECTED",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = account
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db_session] = lambda: mock_db

    with patch(
        "app.modules.telegram_accounts.service.TelegramAccountService.disconnect_account",
        new=AsyncMock(return_value=True),
    ), patch("app.modules.audit.service.AuditService.log_event", new=AsyncMock()):
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete(f"/api/v1/telegram/accounts/{own_account_id}")
                assert resp.status_code == 200
                data = resp.json()
                assert data["success"] is True
                assert "muvaffaqiyatli uzildi" in data["message"]
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sync_chats_endpoint(test_user):
    """Verifies manual sync-chats endpoint works with ownership validation."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    mock_db = AsyncMock()

    own_account_id = uuid.uuid4()
    account = TelegramAccount(
        id=own_account_id,
        user_id=test_user.id,
        telegram_user_id=555444,
        encrypted_session=b"dummy",
        status="CONNECTED",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = account
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db_session] = lambda: mock_db

    with patch(
        "app.modules.telegram_accounts.service.TelegramAccountService.refresh_account_chats",
        new=AsyncMock(return_value=12),
    ), patch("app.modules.audit.service.AuditService.log_event", new=AsyncMock()):
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(f"/api/v1/telegram/accounts/{own_account_id}/sync-chats")
                assert resp.status_code == 200
                data = resp.json()
                assert data["success"] is True
                assert data["synced_count"] == 12
        finally:
            app.dependency_overrides.clear()
