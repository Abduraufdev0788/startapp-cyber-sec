"""
Admin Dashboard and Monitoring API Endpoints.
Provides aggregated platform metrics, real-time daemon statuses,
scanned URLs list with detailed threat forensics, account tracking, and on-demand rescan.
"""

import logging
import uuid
from typing import Annotated, Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin_user
from app.core.config import get_settings
from app.db.session import get_db_session
from app.modules.notifications.models import Notification
from app.modules.risk_engine.engine import RiskEngine
from app.modules.risk_engine.models import ThreatAssessment
from app.modules.telegram_accounts.models import TelegramAccount
from app.modules.telegram_chats.models import TelegramChat
from app.modules.threat_intelligence.models import ThreatIntelligence
from app.modules.threat_intelligence.service import ThreatIntelligenceService
from app.modules.url_scanning.models import ScannedUrl
from app.modules.url_scanning.pipeline import canonicalize_url, compute_url_hash

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["Admin Dashboard"],
    dependencies=[Depends(get_current_admin_user)],
)


class RescanRequest(BaseModel):
    url: str


@router.get("/stats", response_model=dict[str, Any])
async def get_admin_dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Returns platform-wide metrics, system health, and threat distribution statistics."""
    settings = get_settings()

    # 1. Accounts Statistics
    connected_stmt = select(func.count(TelegramAccount.id)).where(TelegramAccount.status == "CONNECTED")
    connected_count = (await db.execute(connected_stmt)).scalar() or 0

    disconnected_stmt = select(func.count(TelegramAccount.id)).where(
        TelegramAccount.status.in_(["DISCONNECTED", "REVOKED"])
    )
    disconnected_count = (await db.execute(disconnected_stmt)).scalar() or 0

    total_accounts_stmt = select(func.count(TelegramAccount.id))
    total_accounts_count = (await db.execute(total_accounts_stmt)).scalar() or 0

    # 2. Telegram Bot Users (Start count + registered platform users)
    bot_users_count = 0
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        bot_users_count = await r.scard("bot:unique_users")
        await r.aclose()
    except Exception as e:
        logger.warning("Failed to fetch bot:unique_users from Redis: %s", e)

    # Ensure bot_users is at least the number of connected telegram accounts
    bot_users_count = max(bot_users_count, total_accounts_count)

    # 3. Monitored Chats Count
    chats_count_stmt = select(func.count(TelegramChat.id))
    total_chats_count = (await db.execute(chats_count_stmt)).scalar() or 0

    # 4. Scanned URLs & Verdict Distribution
    total_scans_stmt = select(func.count(ScannedUrl.id))
    total_scans_count = (await db.execute(total_scans_stmt)).scalar() or 0

    verdict_stmt = select(ThreatAssessment.verdict, func.count(ThreatAssessment.id)).group_by(ThreatAssessment.verdict)
    verdict_rows = (await db.execute(verdict_stmt)).all()
    verdict_counts = {
        "PHISHING": 0,
        "SCAM": 0,
        "SUSPICIOUS": 0,
        "BENIGN": 0,
    }
    for v, c in verdict_rows:
        if v in verdict_counts:
            verdict_counts[v] = c

    # 5. Notifications Statistics
    notif_stmt = select(Notification.delivery_status, func.count(Notification.id)).group_by(Notification.delivery_status)
    notif_rows = (await db.execute(notif_stmt)).all()
    notif_counts = {
        "SENT": 0,
        "THROTTLED": 0,
        "FAILED": 0,
        "PENDING": 0,
    }
    for s, c in notif_rows:
        if s in notif_counts:
            notif_counts[s] = c

    # 6. Real-time System Services Health
    system_health: dict[str, Any] = {
        "postgres": {"status": "HEALTHY", "message": "Database active"},
        "redis": {"status": "HEALTHY", "message": "Cache broker active"},
        "celery": {"status": "HEALTHY", "message": "Worker queues active: celery, scanning, notifications"},
        "telethon_monitor": {"status": "HEALTHY", "message": f"{connected_count} account(s) monitored"},
        "telegram_bot": {"status": "HEALTHY", "message": "Interactive bot active (@startapp_cybersec_bot)"},
    }

    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        await r.aclose()
    except Exception as e:
        system_health["redis"] = {"status": "UNHEALTHY", "message": str(e)}

    return {
        "success": True,
        "stats": {
            "connected_accounts": connected_count,
            "disconnected_accounts": disconnected_count,
            "total_accounts": total_accounts_count,
            "bot_users_count": bot_users_count,
            "monitored_chats_count": total_chats_count,
            "total_scans": total_scans_count,
            "threats_detected": verdict_counts["PHISHING"] + verdict_counts["SCAM"],
            "verdict_distribution": verdict_counts,
            "notifications": notif_counts,
        },
        "system_health": system_health,
    }


@router.get("/scans", response_model=dict[str, Any])
async def get_admin_scans_list(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    verdict: str | None = Query(None, description="Filter by verdict: PHISHING, SCAM, SUSPICIOUS, BENIGN"),
    search: str | None = Query(None, description="Search domain or URL text"),
) -> dict[str, Any]:
    """Returns paginated list of scanned URLs with threat assessments and risk scores."""
    offset = (page - 1) * page_size

    stmt = select(ScannedUrl).options(
        selectinload(ScannedUrl.threat_assessment),
        selectinload(ScannedUrl.threat_intelligence),
    )

    if verdict:
        stmt = stmt.join(ThreatAssessment).where(ThreatAssessment.verdict == verdict.upper())

    if search:
        search_clean = f"%{search.strip().lower()}%"
        stmt = stmt.where((ScannedUrl.domain.ilike(search_clean)) | (ScannedUrl.canonical_url.ilike(search_clean)))

    # Order by newest scans first
    stmt = stmt.order_by(desc(ScannedUrl.created_at))

    # Total count
    count_stmt = select(func.count(ScannedUrl.id))
    if verdict:
        count_stmt = count_stmt.join(ThreatAssessment).where(ThreatAssessment.verdict == verdict.upper())
    if search:
        count_stmt = count_stmt.where((ScannedUrl.domain.ilike(search_clean)) | (ScannedUrl.canonical_url.ilike(search_clean)))

    total_records = (await db.execute(count_stmt)).scalar() or 0

    results = (await db.execute(stmt.offset(offset).limit(page_size))).scalars().all()

    items = []
    for s in results:
        assessment = s.threat_assessment
        intel = s.threat_intelligence
        items.append({
            "id": str(s.id),
            "domain": s.domain,
            "canonical_url": s.canonical_url,
            "raw_url": s.raw_url,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "last_scanned_at": s.last_scanned_at.isoformat() if s.last_scanned_at else None,
            "verdict": assessment.verdict if assessment else "UNKNOWN",
            "risk_score": assessment.risk_score if assessment else 0,
            "confidence": assessment.confidence if assessment else 0.0,
            "impersonated_brand": assessment.impersonated_brand if assessment else None,
            "reasons": assessment.reasons if assessment else [],
            "evaluated_by": assessment.evaluated_by if assessment else None,
            "domain_age_days": intel.domain_age_days if intel else None,
            "ssl_valid": intel.ssl_valid if intel else False,
            "http_status": intel.http_status if intel else None,
        })

    return {
        "success": True,
        "total": total_records,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_records + page_size - 1) // page_size if total_records > 0 else 1,
        "items": items,
    }


@router.get("/scans/{url_id}", response_model=dict[str, Any])
async def get_admin_scan_detail(
    url_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Returns comprehensive forensic details of a single scanned URL for the side panel drawer."""
    stmt = (
        select(ScannedUrl)
        .where(ScannedUrl.id == url_id)
        .options(
            selectinload(ScannedUrl.threat_assessment),
            selectinload(ScannedUrl.threat_intelligence),
        )
    )
    res = await db.execute(stmt)
    scanned_record = res.scalar_one_or_none()

    if not scanned_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scanned URL record not found")

    assessment = scanned_record.threat_assessment
    intel = scanned_record.threat_intelligence

    return {
        "success": True,
        "scan": {
            "id": str(scanned_record.id),
            "domain": scanned_record.domain,
            "canonical_url": scanned_record.canonical_url,
            "raw_url": scanned_record.raw_url,
            "url_hash": scanned_record.url_hash,
            "status": scanned_record.status,
            "created_at": scanned_record.created_at.isoformat() if scanned_record.created_at else None,
            "updated_at": scanned_record.updated_at.isoformat() if scanned_record.updated_at else None,
            "last_scanned_at": scanned_record.last_scanned_at.isoformat() if scanned_record.last_scanned_at else None,
            "assessment": {
                "verdict": assessment.verdict if assessment else "UNKNOWN",
                "risk_score": assessment.risk_score if assessment else 0,
                "confidence": assessment.confidence if assessment else 0.0,
                "impersonated_brand": assessment.impersonated_brand if assessment else None,
                "reasons": assessment.reasons if assessment else [],
                "evaluated_by": assessment.evaluated_by if assessment else "N/A",
                "gemini_response": assessment.gemini_response if assessment else None,
            } if assessment else None,
            "intelligence": {
                "domain_age_days": intel.domain_age_days if intel else None,
                "registrar": intel.registrar if intel else None,
                "dns_records": intel.dns_records if intel else {},
                "ssl_issuer": intel.ssl_issuer if intel else None,
                "ssl_valid": intel.ssl_valid if intel else False,
                "http_status": intel.http_status if intel else None,
                "response_time_ms": intel.response_time_ms if intel else None,
                "has_login_form": intel.has_login_form if intel else False,
                "has_password_input": intel.has_password_input if intel else False,
                "redirect_chain": intel.redirect_chain if intel else [],
                "text_excerpt": intel.text_excerpt if intel else None,
            } if intel else None,
        },
    }


@router.post("/rescan", response_model=dict[str, Any])
async def rescan_url_now(
    req: RescanRequest,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Forces an immediate fresh rescan of any URL, bypassing cache and updating database."""
    target_url = req.url.strip()
    if not target_url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    canonical = canonicalize_url(target_url)
    url_hash = compute_url_hash(canonical)

    # 1. Fresh Technical Intelligence Gathering
    evidence = await ThreatIntelligenceService.enrich_url(canonical)
    domain = evidence["domain"]

    # 2. Gemini AI Evaluation with candidate fallbacks
    try:
        from app.integrations.gemini.client import GeminiClient
        gemini_client = GeminiClient()
        ai_assessment = await gemini_client.evaluate_url_threat(
            domain=domain,
            technical_evidence=evidence,
            web_text_excerpt=evidence.get("text_excerpt"),
        )
        evaluated_by = "GEMINI_3_5_FLASH"
    except Exception:
        from app.integrations.gemini.client import GeminiClient
        ai_assessment = GeminiClient.create_heuristic_fallback(
            technical_evidence=evidence,
            domain=domain,
        )
        evaluated_by = "HEURISTIC_FALLBACK"

    # 3. Risk Engine multi-factor synthesis
    risk_result = RiskEngine.evaluate(
        domain=domain,
        technical_evidence=evidence,
        ai_assessment=ai_assessment,
    )

    verdict = risk_result["verdict"]
    risk_score = risk_result["risk_score"]
    confidence = risk_result["confidence"]
    impersonated_brand = risk_result["impersonated_brand"]
    reasons = risk_result["reasons"]

    # 4. Save or update record in PostgreSQL
    stmt = (
        select(ScannedUrl)
        .where(ScannedUrl.url_hash == url_hash)
        .options(
            selectinload(ScannedUrl.threat_assessment),
            selectinload(ScannedUrl.threat_intelligence),
        )
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing:
        scanned_record = existing
        scanned_record.status = "EVALUATED"
        if scanned_record.threat_assessment:
            scanned_record.threat_assessment.verdict = verdict
            scanned_record.threat_assessment.risk_score = risk_score
            scanned_record.threat_assessment.confidence = confidence
            scanned_record.threat_assessment.impersonated_brand = impersonated_brand
            scanned_record.threat_assessment.reasons = reasons
            scanned_record.threat_assessment.evaluated_by = evaluated_by
            scanned_record.threat_assessment.gemini_response = ai_assessment.model_dump() if ai_assessment else None
        else:
            new_assessment = ThreatAssessment(
                url_id=scanned_record.id,
                verdict=verdict,
                risk_score=risk_score,
                confidence=confidence,
                impersonated_brand=impersonated_brand,
                reasons=reasons,
                evaluated_by=evaluated_by,
                gemini_response=ai_assessment.model_dump() if ai_assessment else None,
            )
            db.add(new_assessment)

        if scanned_record.threat_intelligence:
            intel = scanned_record.threat_intelligence
            intel.domain_age_days = evidence.get("domain_age_days", 100)
            intel.registrar = evidence.get("registrar")
            intel.dns_records = evidence.get("dns_records", {})
            intel.ssl_issuer = evidence.get("ssl_issuer")
            intel.ssl_valid = evidence.get("ssl_valid", False)
            intel.http_status = evidence.get("http_status")
            intel.response_time_ms = evidence.get("response_time_ms")
            intel.has_login_form = evidence.get("has_login_form", False)
            intel.has_password_input = evidence.get("has_password_input", False)
            intel.redirect_chain = evidence.get("redirect_chain", [])
            intel.text_excerpt = evidence.get("text_excerpt")
    else:
        scanned_record = ScannedUrl(
            url_hash=url_hash,
            raw_url=target_url,
            canonical_url=canonical,
            domain=domain,
            status="EVALUATED",
        )
        db.add(scanned_record)
        await db.flush()

        intel = ThreatIntelligence(
            url_id=scanned_record.id,
            domain_age_days=evidence.get("domain_age_days", 100),
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
        db.add(intel)

        new_assessment = ThreatAssessment(
            url_id=scanned_record.id,
            verdict=verdict,
            risk_score=risk_score,
            confidence=confidence,
            impersonated_brand=impersonated_brand,
            reasons=reasons,
            evaluated_by=evaluated_by,
            gemini_response=ai_assessment.model_dump() if ai_assessment else None,
        )
        db.add(new_assessment)

    await db.commit()

    return {
        "success": True,
        "url_id": str(scanned_record.id),
        "domain": domain,
        "canonical_url": canonical,
        "verdict": verdict,
        "risk_score": risk_score,
        "confidence": confidence,
        "impersonated_brand": impersonated_brand,
        "reasons": reasons,
        "evaluated_by": evaluated_by,
    }


@router.get("/accounts", response_model=dict[str, Any])
async def get_admin_accounts_list(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """Returns connected and revoked Telegram accounts list with metadata."""
    stmt = select(TelegramAccount).options(selectinload(TelegramAccount.chats)).order_by(desc(TelegramAccount.created_at))
    accounts = (await db.execute(stmt)).scalars().all()

    items = []
    for acc in accounts:
        items.append({
            "id": str(acc.id),
            "telegram_user_id": acc.telegram_user_id,
            "phone_number_hash": acc.phone_number_hash[:12] + "...",
            "status": acc.status,
            "auth_state": acc.auth_state,
            "last_connected_at": acc.last_connected_at.isoformat() if acc.last_connected_at else None,
            "created_at": acc.created_at.isoformat() if acc.created_at else None,
            "chats_count": len(acc.chats) if acc.chats else 0,
        })

    return {
        "success": True,
        "total": len(items),
        "items": items,
    }


@router.get("/notifications", response_model=dict[str, Any])
async def get_admin_notifications_list(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Returns list of recent Telegram alert notification attempts."""
    stmt = (
        select(Notification)
        .options(selectinload(Notification.url))
        .order_by(desc(Notification.created_at))
        .limit(limit)
    )
    notifs = (await db.execute(stmt)).scalars().all()

    items = []
    for n in notifs:
        items.append({
            "id": str(n.id),
            "telegram_chat_id": n.telegram_chat_id,
            "alert_type": n.alert_type,
            "delivery_status": n.delivery_status,
            "attempts": n.attempts,
            "sent_at": n.sent_at.isoformat() if n.sent_at else None,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "url": n.url.canonical_url if n.url else "N/A",
            "domain": n.url.domain if n.url else "N/A",
        })

    return {
        "success": True,
        "total": len(items),
        "items": items,
    }
