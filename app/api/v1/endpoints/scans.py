"""
URL Scanning and Threat Assessment Endpoints.
"""

import uuid
from datetime import UTC
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.exceptions import ResourceNotFoundException
from app.core.rate_limit import rate_limit
from app.db.session import get_db_session
from app.integrations.gemini.client import GeminiClient
from app.modules.audit.service import AuditService
from app.modules.risk_engine.engine import RiskEngine
from app.modules.risk_engine.models import ThreatAssessment
from app.modules.threat_intelligence.models import ThreatIntelligence
from app.modules.threat_intelligence.service import ThreatIntelligenceService
from app.modules.url_scanning.models import ScannedUrl
from app.modules.url_scanning.pipeline import canonicalize_url, compute_url_hash
from app.modules.users.models import User

router = APIRouter(prefix="/scans", tags=["URL Scans"])


class ScanUrlRequest(BaseModel):
    """Request payload for submitting a URL to scan."""
    url: str


class ScanUrlResponseData(BaseModel):
    """Response payload containing scan results."""
    scan_id: uuid.UUID
    canonical_url: str
    domain: str
    status: str
    verdict: str
    risk_score: int
    confidence: float
    impersonated_brand: str | None
    reasons: list[str]


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(rate_limit(times=30, seconds=60, key_prefix="rl_scan"))],
)
async def scan_url_endpoint(
    payload: ScanUrlRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """
    Submits a URL to be scanned for phishing and fraud.
    Performs normalization, SSRF check, technical enrichment, and AI risk analysis.
    """
    canonical = canonicalize_url(payload.url)
    url_hash = compute_url_hash(canonical)

    # 1. Check if URL was already scanned and cached in DB
    existing_stmt = (
        select(ScannedUrl)
        .where(ScannedUrl.url_hash == url_hash)
        .options(
            selectinload(ScannedUrl.threat_assessment),
            selectinload(ScannedUrl.threat_intelligence),
        )
    )
    result = await db.execute(existing_stmt)
    scanned_record = result.scalar_one_or_none()

    if scanned_record and scanned_record.threat_assessment:
        assessment = scanned_record.threat_assessment
        return {
            "success": True,
            "data": {
                "scan_id": str(scanned_record.id),
                "canonical_url": scanned_record.canonical_url,
                "domain": scanned_record.domain,
                "status": scanned_record.status,
                "verdict": assessment.verdict,
                "risk_score": assessment.risk_score,
                "confidence": assessment.confidence,
                "impersonated_brand": assessment.impersonated_brand,
                "reasons": assessment.reasons,
                "cached": True,
            },
        }

    # 2. Perform fresh technical enrichment with SSRF protection
    evidence = await ThreatIntelligenceService.enrich_url(canonical)
    domain = evidence["domain"]

    # 3. Perform AI threat evaluation using Gemini (with heuristic fallback)
    try:
        gemini_client = GeminiClient()
        ai_assessment = await gemini_client.evaluate_url_threat(
            domain=domain,
            technical_evidence=evidence,
            web_text_excerpt=evidence.get("text_excerpt"),
        )
        evaluated_by = "GEMINI_1_5_FLASH"
    except Exception:
        ai_assessment = GeminiClient.create_heuristic_fallback(
            technical_evidence=evidence,
            domain=domain,
        )
        evaluated_by = "HEURISTIC_FALLBACK"

    # 4. Synthesize final multi-factor risk score
    risk_result = RiskEngine.evaluate(
        domain=domain,
        technical_evidence=evidence,
        ai_assessment=ai_assessment,
    )

    # 5. Persist into PostgreSQL
    if not scanned_record:
        scanned_record = ScannedUrl(
            url_hash=url_hash,
            raw_url=payload.url,
            canonical_url=canonical,
            domain=domain,
            status="EVALUATED",
        )
        db.add(scanned_record)
        await db.flush()

    threat_intel = ThreatIntelligence(
        url_id=scanned_record.id,
        domain_age_days=evidence.get("domain_age_days", 0),
        registrar=evidence.get("registrar"),
        dns_records=evidence.get("dns_records", {}),
        ssl_issuer=evidence.get("ssl_issuer"),
        ssl_valid=evidence.get("ssl_valid", False),
        http_status=evidence.get("http_status"),
        response_time_ms=evidence.get("response_time_ms"),
        has_login_form=evidence.get("has_login_form", False),
        has_password_input=evidence.get("has_password_input", False),
        redirect_chain=evidence.get("redirect_chain", []),
        text_excerpt=evidence.get("text_excerpt"),
    )
    db.add(threat_intel)

    assessment = ThreatAssessment(
        url_id=scanned_record.id,
        verdict=risk_result["verdict"],
        risk_score=risk_result["risk_score"],
        confidence=risk_result["confidence"],
        impersonated_brand=risk_result["impersonated_brand"],
        reasons=risk_result["reasons"],
        gemini_response=ai_assessment.model_dump() if ai_assessment else None,
        evaluated_by=evaluated_by,
    )
    db.add(assessment)
    await db.commit()

    return {
        "success": True,
        "data": {
            "scan_id": str(scanned_record.id),
            "canonical_url": scanned_record.canonical_url,
            "domain": scanned_record.domain,
            "status": "EVALUATED",
            "verdict": assessment.verdict,
            "risk_score": assessment.risk_score,
            "confidence": assessment.confidence,
            "impersonated_brand": assessment.impersonated_brand,
            "reasons": assessment.reasons,
            "cached": False,
        },
    }


@router.get("", status_code=status.HTTP_200_OK)
async def list_scans_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = 20,
    offset: int = 0,
    verdict: str | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    """Retrieves paginated scan history with optional filters."""
    from sqlalchemy import desc

    stmt = (
        select(ScannedUrl)
        .options(
            selectinload(ScannedUrl.threat_assessment),
            selectinload(ScannedUrl.threat_intelligence),
        )
        .order_by(desc(ScannedUrl.created_at))
        .limit(min(limit, 100))
        .offset(offset)
    )

    if domain:
        stmt = stmt.where(ScannedUrl.domain.ilike(f"%{domain}%"))

    result = await db.execute(stmt)
    records = result.scalars().all()

    items = []
    for record in records:
        assessment = record.threat_assessment
        if verdict and assessment and assessment.verdict.upper() != verdict.upper():
            continue
        items.append({
            "scan_id": str(record.id),
            "canonical_url": record.canonical_url,
            "domain": record.domain,
            "status": record.status,
            "verdict": assessment.verdict if assessment else "UNKNOWN",
            "risk_score": assessment.risk_score if assessment else 0,
            "confidence": assessment.confidence if assessment else 0.0,
            "impersonated_brand": assessment.impersonated_brand if assessment else None,
            "reasons": assessment.reasons if assessment else [],
            "scanned_at": record.last_scanned_at.isoformat() if record.last_scanned_at else None,
        })

    return {
        "success": True,
        "count": len(items),
        "limit": limit,
        "offset": offset,
        "data": items,
    }


@router.get("/{scan_id}", status_code=status.HTTP_200_OK)
async def get_scan_by_id(
    scan_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Retrieves an existing scan result by its ID."""
    stmt = (
        select(ScannedUrl)
        .where(ScannedUrl.id == scan_id)
        .options(
            selectinload(ScannedUrl.threat_assessment),
            selectinload(ScannedUrl.threat_intelligence),
        )
    )
    result = await db.execute(stmt)
    scanned_record = result.scalar_one_or_none()

    if not scanned_record or not scanned_record.threat_assessment:
        raise ResourceNotFoundException("Scan report not found.")

    assessment = scanned_record.threat_assessment
    intel = scanned_record.threat_intelligence
    return {
        "success": True,
        "data": {
            "scan_id": str(scanned_record.id),
            "canonical_url": scanned_record.canonical_url,
            "domain": scanned_record.domain,
            "status": scanned_record.status,
            "verdict": assessment.verdict,
            "risk_score": assessment.risk_score,
            "confidence": assessment.confidence,
            "impersonated_brand": assessment.impersonated_brand,
            "reasons": assessment.reasons,
            "technical_evidence": {
                "domain_age_days": intel.domain_age_days if intel else None,
                "registrar": intel.registrar if intel else None,
                "ssl_valid": intel.ssl_valid if intel else None,
                "http_status": intel.http_status if intel else None,
                "dns_records": intel.dns_records if intel else None,
            } if intel else None,
        },
    }


@router.post("/{scan_id}/rescan", status_code=status.HTTP_200_OK)
async def rescan_url_endpoint(
    scan_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Forces a fresh re-scan and evaluation of a previously scanned URL."""
    stmt = (
        select(ScannedUrl)
        .where(ScannedUrl.id == scan_id)
        .options(
            selectinload(ScannedUrl.threat_assessment),
            selectinload(ScannedUrl.threat_intelligence),
        )
    )
    result = await db.execute(stmt)
    scanned_record = result.scalar_one_or_none()

    if not scanned_record:
        raise ResourceNotFoundException("Scan report not found.")

    canonical = scanned_record.canonical_url

    # Perform fresh enrichment
    evidence = await ThreatIntelligenceService.enrich_url(canonical)
    domain = evidence["domain"]

    # AI Threat evaluation
    try:
        gemini_client = GeminiClient()
        ai_assessment = await gemini_client.evaluate_url_threat(
            domain=domain,
            technical_evidence=evidence,
            web_text_excerpt=evidence.get("text_excerpt"),
        )
        evaluated_by = "GEMINI_1_5_FLASH"
    except Exception:
        ai_assessment = GeminiClient.create_heuristic_fallback(
            technical_evidence=evidence,
            domain=domain,
        )
        evaluated_by = "HEURISTIC_FALLBACK"

    risk_result = RiskEngine.evaluate(
        domain=domain,
        technical_evidence=evidence,
        ai_assessment=ai_assessment,
    )

    # Update intelligence
    if scanned_record.threat_intelligence:
        intel = scanned_record.threat_intelligence
        intel.domain_age_days = evidence.get("domain_age_days", 0)
        intel.registrar = evidence.get("registrar")
        intel.dns_records = evidence.get("dns_records", {})
        intel.ssl_valid = evidence.get("ssl_valid", False)
        intel.http_status = evidence.get("http_status")
        intel.response_time_ms = evidence.get("response_time_ms")
        intel.has_login_form = evidence.get("has_login_form", False)
        intel.has_password_input = evidence.get("has_password_input", False)
        intel.redirect_chain = evidence.get("redirect_chain", [])
        intel.text_excerpt = evidence.get("text_excerpt")

    # Update assessment
    if scanned_record.threat_assessment:
        assessment = scanned_record.threat_assessment
        assessment.verdict = risk_result["verdict"]
        assessment.risk_score = risk_result["risk_score"]
        assessment.confidence = risk_result["confidence"]
        assessment.impersonated_brand = risk_result["impersonated_brand"]
        assessment.reasons = risk_result["reasons"]
        assessment.gemini_response = ai_assessment.model_dump() if ai_assessment else None
        assessment.evaluated_by = evaluated_by

    from datetime import datetime
    scanned_record.last_scanned_at = datetime.now(UTC)
    scanned_record.status = "EVALUATED"
    await db.commit()

    await AuditService.log_event(
        db=db,
        action="THREAT_RESCAN",
        user_id=current_user.id,
        details={"scan_id": str(scanned_record.id), "domain": domain, "verdict": risk_result["verdict"]},
    )

    return {
        "success": True,
        "message": "Havola qayta skan qilindi va tahlil yangilandi.",
        "data": {
            "scan_id": str(scanned_record.id),
            "canonical_url": scanned_record.canonical_url,
            "domain": scanned_record.domain,
            "status": scanned_record.status,
            "verdict": risk_result["verdict"],
            "risk_score": risk_result["risk_score"],
            "confidence": risk_result["confidence"],
            "impersonated_brand": risk_result["impersonated_brand"],
            "reasons": risk_result["reasons"],
            "cached": False,
        },
    }
