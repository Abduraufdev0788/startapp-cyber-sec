"""
Unit tests for Admin Dashboard API endpoints (/api/v1/admin/*).
Verifies stats calculation, scans pagination, forensic details, and accounts endpoints.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db_session
from app.main import app
from app.modules.risk_engine.models import ThreatAssessment
from app.modules.threat_intelligence.models import ThreatIntelligence
from app.modules.url_scanning.models import ScannedUrl


@pytest.mark.asyncio
async def test_get_admin_stats_endpoint():
    """Verifies GET /api/v1/admin/stats returns metrics and system health."""
    mock_db = AsyncMock()

    # Mock count queries scalar returns
    mock_scalar = MagicMock()
    mock_scalar.scalar.return_value = 5
    mock_scalar.all.return_value = [("SCAM", 2), ("BENIGN", 3)]
    mock_db.execute.return_value = mock_scalar

    app.dependency_overrides[get_db_session] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/admin/stats")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "stats" in data
    assert "system_health" in data
    assert "connected_accounts" in data["stats"]
    assert "verdict_distribution" in data["stats"]


@pytest.mark.asyncio
async def test_get_admin_scans_list_endpoint():
    """Verifies GET /api/v1/admin/scans returns paginated results."""
    mock_db = AsyncMock()

    url_record = ScannedUrl(
        id=uuid.uuid4(),
        canonical_url="https://uz.1xbet.com/ru/slots",
        domain="uz.1xbet.com",
        status="EVALUATED",
        last_scanned_at=datetime.now(UTC),
    )
    url_record.threat_assessment = ThreatAssessment(
        id=uuid.uuid4(),
        url_id=url_record.id,
        verdict="SCAM",
        risk_score=78,
        confidence=0.9,
        impersonated_brand="1xBet",
        reasons=["Illegal casino"],
        evaluated_by="GEMINI_3_5_FLASH",
    )
    url_record.threat_intelligence = ThreatIntelligence(
        id=uuid.uuid4(),
        url_id=url_record.id,
        domain_age_days=100,
        ssl_valid=True,
        http_status=200,
    )

    mock_count = MagicMock()
    mock_count.scalar.return_value = 1

    mock_items = MagicMock()
    mock_items.scalars.return_value.all.return_value = [url_record]

    mock_db.execute.side_effect = [mock_count, mock_items]
    app.dependency_overrides[get_db_session] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/admin/scans?page=1&page_size=10")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["domain"] == "uz.1xbet.com"
    assert data["items"][0]["verdict"] == "SCAM"


@pytest.mark.asyncio
async def test_get_admin_scan_detail_endpoint():
    """Verifies GET /api/v1/admin/scans/{id} returns full forensic data for slide-over drawer."""
    mock_db = AsyncMock()
    test_id = uuid.uuid4()

    url_record = ScannedUrl(
        id=test_id,
        canonical_url="https://uz.1xbet.com/ru/slots",
        raw_url="https://uz.1xbet.com/ru/slots",
        domain="uz.1xbet.com",
        url_hash="hash123",
        status="EVALUATED",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        last_scanned_at=datetime.now(UTC),
    )
    url_record.threat_assessment = ThreatAssessment(
        id=uuid.uuid4(),
        url_id=test_id,
        verdict="SCAM",
        risk_score=78,
        confidence=0.9,
        impersonated_brand="1xBet",
        reasons=["High risk predatory gambling trap"],
        evaluated_by="GEMINI_3_5_FLASH",
    )
    url_record.threat_intelligence = ThreatIntelligence(
        id=uuid.uuid4(),
        url_id=test_id,
        domain_age_days=100,
        ssl_valid=True,
        http_status=200,
        has_login_form=False,
        has_password_input=False,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = url_record
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db_session] = lambda: mock_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(f"/api/v1/admin/scans/{test_id}")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["scan"]["domain"] == "uz.1xbet.com"
    assert data["scan"]["assessment"]["risk_score"] == 78
    assert "reasons" in data["scan"]["assessment"]
    assert "intelligence" in data["scan"]
