"""
Unit and integration tests for Notifications & Active Alerts API endpoints (/api/v1/notifications).
Verifies active alert retrieval, dismissal lifecycle, and anti-IDOR isolation.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.main import app
from app.modules.notifications.models import Notification
from app.modules.risk_engine.models import ThreatAssessment
from app.modules.url_scanning.models import ScannedUrl
from app.modules.users.models import User


@pytest.fixture
def test_user():
    return User(
        id=uuid.uuid4(),
        email="alert_user@phishguard.uz",
        hashed_password="pw",
        role="USER",
        is_active=True,
    )


@pytest.mark.asyncio
async def test_get_active_alerts_endpoint(test_user):
    """Verifies GET /api/v1/notifications/active returns active alerts for current user."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    mock_db = AsyncMock()

    mock_url = ScannedUrl(
        id=uuid.uuid4(),
        canonical_url="https://payme-security-check.com/login",
        domain="payme-security-check.com",
    )
    mock_url.threat_assessment = ThreatAssessment(
        id=uuid.uuid4(),
        url_id=mock_url.id,
        verdict="MALICIOUS",
        risk_score=92,
        confidence=0.95,
        impersonated_brand="Payme",
        reasons=["Spoofed domain", "Credential harvesting form"],
    )

    notif = Notification(
        id=uuid.uuid4(),
        user_id=test_user.id,
        url_id=mock_url.id,
        telegram_chat_id=123456789,
        alert_type="THREAT_FOUND",
        delivery_status="SENT",
        is_dismissed=False,
    )
    notif.created_at = datetime.now(UTC)
    notif.url = mock_url

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [notif]
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db_session] = lambda: mock_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/notifications/active")
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["has_active_alerts"] is True
            assert data["count"] == 1
            alert = data["data"][0]
            assert alert["domain"] == "payme-security-check.com"
            assert "hxxps://" in alert["defanged_url"]
            assert alert["verdict"] == "MALICIOUS"
            assert alert["risk_score"] == 92
            assert alert["impersonated_brand"] == "Payme"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dismiss_alert_success(test_user):
    """Verifies POST /api/v1/notifications/{id}/dismiss dismisses own alert."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    mock_db = AsyncMock()

    notif_id = uuid.uuid4()
    notif = Notification(
        id=notif_id,
        user_id=test_user.id,
        url_id=uuid.uuid4(),
        telegram_chat_id=123456789,
        alert_type="THREAT_FOUND",
        delivery_status="SENT",
        is_dismissed=False,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = notif
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db_session] = lambda: mock_db

    with patch("app.modules.audit.service.AuditService.log_event", new=AsyncMock()):
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(f"/api/v1/notifications/{notif_id}/dismiss")
                assert resp.status_code == 200
                data = resp.json()
                assert data["success"] is True
                assert data["data"]["is_dismissed"] is True
                assert notif.is_dismissed is True
                assert notif.dismissed_at is not None
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_anti_idor_dismiss_other_user_alert(test_user):
    """Verifies that dismissing another user's alert is rejected with 404."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    mock_db = AsyncMock()

    # Query for notification with notification_id and current_user.id returns None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db_session] = lambda: mock_db

    victim_notif_id = uuid.uuid4()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(f"/api/v1/notifications/{victim_notif_id}/dismiss")
            assert resp.status_code == 404
            assert "topilmadi" in resp.json()["error"]["message"]
    finally:
        app.dependency_overrides.clear()
