"""
Unit and integration tests for /api/v1/auth endpoints.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.core.security import hash_password
from app.db.session import get_db_session
from app.main import app
from app.modules.users.models import User


@pytest.mark.asyncio
async def test_auth_register_and_login_flow():
    """Tests registration and login mock flow."""
    mock_user_id = uuid.uuid4()
    mock_user = User(
        id=mock_user_id,
        email="test@phishguard.uz",
        hashed_password=hash_password("SecurePassword123!"),
        role="USER",
        is_active=True,
    )

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    # Mock no existing user on check, then return mock_user
    mock_result_empty = MagicMock()
    mock_result_empty.scalar_one_or_none.return_value = None

    mock_db.execute.return_value = mock_result_empty

    app.dependency_overrides[get_db_session] = lambda: mock_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Register
            reg_resp = await client.post(
                "/api/v1/auth/register",
                json={"email": "newuser@phishguard.uz", "password": "NewUserPassword123!"},
            )
            assert reg_resp.status_code == 201
            reg_data = reg_resp.json()
            assert reg_data["success"] is True
            assert "access_token" in reg_data["data"]
            assert "refresh_token" in reg_data["data"]
            refresh_token = reg_data["data"]["refresh_token"]

            # 2. Login with correct password
            mock_result_found = MagicMock()
            mock_result_found.scalar_one_or_none.return_value = mock_user
            mock_db.execute.return_value = mock_result_found

            login_resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "test@phishguard.uz", "password": "SecurePassword123!"},
            )
            assert login_resp.status_code == 200
            login_data = login_resp.json()
            assert login_data["success"] is True
            assert "access_token" in login_data["data"]

            # 3. Refresh token
            refresh_resp = await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            assert refresh_resp.status_code == 200
            refresh_data = refresh_resp.json()
            assert refresh_data["success"] is True
            assert "access_token" in refresh_data["data"]

            # 4. Login with wrong password
            wrong_login = await client.post(
                "/api/v1/auth/login",
                json={"email": "test@phishguard.uz", "password": "WrongPassword!"},
            )
            assert wrong_login.status_code == 401
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_me_endpoint():
    """Tests /api/v1/auth/me returns current user profile."""
    mock_user = User(
        id=uuid.uuid4(),
        email="analyst@phishguard.uz",
        hashed_password="hash",
        role="ANALYST",
        is_active=True,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer dummy_token"},
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["email"] == "analyst@phishguard.uz"
            assert data["role"] == "ANALYST"
    finally:
        app.dependency_overrides.clear()
