"""
Unit and integration tests for Scans API endpoints (/api/v1/scans).
Verifies scan history pagination, individual scan reports, and re-scan capabilities.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.integrations.gemini.schemas import GeminiPhishingAssessment, VerdictEnum
from app.main import app
from app.modules.risk_engine.models import ThreatAssessment
from app.modules.threat_intelligence.models import ThreatIntelligence
from app.modules.url_scanning.models import ScannedUrl
from app.modules.users.models import User


@pytest.fixture
def test_user():
    return User(
        id=uuid.uuid4(),
        email="analyst_scanner@phishguard.uz",
        hashed_password="pw",
        role="ANALYST",
        is_active=True,
    )


@pytest.mark.asyncio
async def test_list_scans_endpoint(test_user):
    """Verifies GET /api/v1/scans returns paginated scan records."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    mock_db = AsyncMock()

    url_record = ScannedUrl(
        id=uuid.uuid4(),
        canonical_url="https://fake-login-bank.xyz",
        domain="fake-login-bank.xyz",
        status="EVALUATED",
        last_scanned_at=datetime.now(UTC),
    )
    url_record.threat_assessment = ThreatAssessment(
        id=uuid.uuid4(),
        url_id=url_record.id,
        verdict="MALICIOUS",
        risk_score=95,
        confidence=0.99,
        impersonated_brand="National Bank",
        reasons=["Spoofed credential harvesting form"],
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [url_record]
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db_session] = lambda: mock_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/scans?limit=10&offset=0")
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["count"] == 1
            item = data["data"][0]
            assert item["domain"] == "fake-login-bank.xyz"
            assert item["verdict"] == "MALICIOUS"
            assert item["risk_score"] == 95
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_scan_by_id(test_user):
    """Verifies GET /api/v1/scans/{id} returns detailed scan information."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    mock_db = AsyncMock()

    scan_id = uuid.uuid4()
    url_record = ScannedUrl(
        id=scan_id,
        canonical_url="https://safe-company-portal.com",
        domain="safe-company-portal.com",
        status="EVALUATED",
    )
    url_record.threat_assessment = ThreatAssessment(
        id=uuid.uuid4(),
        url_id=scan_id,
        verdict="BENIGN",
        risk_score=5,
        confidence=0.9,
        impersonated_brand=None,
        reasons=["Legitimate enterprise site"],
        evaluated_by="GEMINI_1_5_FLASH",
    )
    url_record.threat_intelligence = ThreatIntelligence(
        id=uuid.uuid4(),
        url_id=scan_id,
        domain_age_days=1500,
        registrar="MarkMonitor",
        ssl_valid=True,
        http_status=200,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = url_record
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db_session] = lambda: mock_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/api/v1/scans/{scan_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["data"]["verdict"] == "BENIGN"
            assert data["data"]["technical_evidence"]["ssl_valid"] is True
            assert data["data"]["technical_evidence"]["domain_age_days"] == 1500
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rescan_url_endpoint(test_user):
    """Verifies POST /api/v1/scans/{id}/rescan triggers fresh enrichment and audit logging."""
    app.dependency_overrides[get_current_user] = lambda: test_user
    mock_db = AsyncMock()

    scan_id = uuid.uuid4()
    url_record = ScannedUrl(
        id=scan_id,
        canonical_url="https://suspicious-promo.click",
        domain="suspicious-promo.click",
        status="EVALUATED",
    )
    url_record.threat_assessment = ThreatAssessment(
        id=uuid.uuid4(),
        url_id=scan_id,
        verdict="SUSPICIOUS",
        risk_score=65,
        confidence=0.8,
        impersonated_brand=None,
        reasons=[],
    )
    url_record.threat_intelligence = ThreatIntelligence(
        id=uuid.uuid4(),
        url_id=scan_id,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = url_record
    mock_db.execute.return_value = mock_result
    app.dependency_overrides[get_db_session] = lambda: mock_db

    mock_evidence = {
        "domain": "suspicious-promo.click",
        "domain_age_days": 2,
        "registrar": "NameCheap",
        "dns_records": {"A": ["1.2.3.4"]},
        "ssl_valid": False,
        "http_status": 200,
        "response_time_ms": 120,
        "has_login_form": True,
        "has_password_input": True,
        "redirect_chain": [],
        "text_excerpt": "Login to win 1,000,000 UZS",
    }

    mock_ai_schema = GeminiPhishingAssessment(
        verdict=VerdictEnum.PHISHING,
        risk_score=90,
        confidence=0.95,
        impersonated_brand="Click",
        reasons=["Fake brand giveaway and credential form"],
        evidence_matches=["fake_login_form"],
    )

    with patch(
        "app.modules.threat_intelligence.service.ThreatIntelligenceService.enrich_url",
        new=AsyncMock(return_value=mock_evidence),
    ), patch(
        "app.integrations.gemini.client.GeminiClient.evaluate_url_threat",
        new=AsyncMock(return_value=mock_ai_schema),
    ), patch("app.modules.audit.service.AuditService.log_event", new=AsyncMock()) as mock_audit:
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(f"/api/v1/scans/{scan_id}/rescan")
                assert resp.status_code == 200
                data = resp.json()
                assert data["success"] is True
                assert data["data"]["verdict"] in ["PHISHING", "MALICIOUS"]
                assert data["data"]["risk_score"] >= 90
                assert mock_audit.await_count == 1
        finally:
            app.dependency_overrides.clear()
