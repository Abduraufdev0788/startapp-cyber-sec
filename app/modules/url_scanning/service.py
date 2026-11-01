"""
URL Scanning and Threat Evaluation Domain Service.
Provides unified scanning logic with caching in PostgreSQL, SSRF defense,
technical enrichment, Gemini AI analysis, and multi-factor risk scoring.
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_standalone_db_session
from app.integrations.gemini.client import GeminiClient
from app.modules.risk_engine.engine import RiskEngine
from app.modules.risk_engine.models import ThreatAssessment
from app.modules.threat_intelligence.models import ThreatIntelligence
from app.modules.threat_intelligence.service import ThreatIntelligenceService
from app.modules.url_scanning.models import ScannedUrl
from app.modules.url_scanning.pipeline import canonicalize_url, compute_url_hash

logger = logging.getLogger(__name__)


class UrlScanService:
    """Core service for scanning URLs with local PostgreSQL cache-first strategy."""

    @classmethod
    async def scan_and_evaluate(cls, raw_url: str) -> dict[str, Any]:
        """
        Scans a URL. Checks database cache first:
        - If previously scanned, returns cached assessment immediately (0 token cost, instant).
        - If new, enriches via DNS/TLS/HTTP (SSRF protected), queries Gemini AI,
          computes multi-factor risk score, and caches record in PostgreSQL.
        """
        canonical = canonicalize_url(raw_url)
        url_hash = compute_url_hash(canonical)

        async with get_standalone_db_session() as db:
            # 1. Check existing cached scan in DB
            stmt = (
                select(ScannedUrl)
                .where(ScannedUrl.url_hash == url_hash)
                .options(
                    selectinload(ScannedUrl.threat_assessment),
                    selectinload(ScannedUrl.threat_intelligence),
                )
            )
            res = await db.execute(stmt)
            scanned_record = res.scalar_one_or_none()

            if scanned_record and scanned_record.threat_assessment:
                assessment = scanned_record.threat_assessment
                logger.info("Cache HIT for URL: %s (Verdict: %s, Score: %d)", canonical, assessment.verdict, assessment.risk_score)
                return {
                    "scan_id": str(scanned_record.id),
                    "canonical_url": scanned_record.canonical_url,
                    "domain": scanned_record.domain,
                    "status": scanned_record.status,
                    "verdict": assessment.verdict,
                    "risk_score": assessment.risk_score,
                    "confidence": assessment.confidence,
                    "impersonated_brand": assessment.impersonated_brand,
                    "reasons": assessment.reasons or [],
                    "cached": True,
                    "evaluated_by": assessment.evaluated_by,
                }

            # 2. Fresh enrichment with SSRF protection
            logger.info("Cache MISS for URL: %s. Performing technical enrichment...", canonical)
            evidence = await ThreatIntelligenceService.enrich_url(canonical)
            domain = evidence.get("domain", "")

            # 3. Gemini AI Analysis (with heuristic fallback)
            try:
                gemini_client = GeminiClient()
                ai_assessment = await gemini_client.evaluate_url_threat(
                    domain=domain,
                    technical_evidence=evidence,
                    web_text_excerpt=evidence.get("text_excerpt"),
                )
                evaluated_by = "GEMINI_1_5_FLASH"
            except Exception as e:
                logger.warning("Gemini AI failed, using heuristic fallback for %s: %s", domain, e)
                ai_assessment = GeminiClient.create_heuristic_fallback(
                    technical_evidence=evidence,
                    domain=domain,
                )
                evaluated_by = "HEURISTIC_FALLBACK"

            # 4. Multi-factor Risk Engine
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

            # 5. Persist to PostgreSQL
            if not scanned_record:
                scanned_record = ScannedUrl(
                    url_hash=url_hash,
                    raw_url=raw_url,
                    canonical_url=canonical,
                    domain=domain,
                    status="EVALUATED",
                )
                db.add(scanned_record)
                await db.flush()

            intel = ThreatIntelligence(
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
            db.add(intel)

            new_assessment = ThreatAssessment(
                url_id=scanned_record.id,
                verdict=verdict,
                risk_score=risk_score,
                confidence=confidence,
                impersonated_brand=impersonated_brand,
                reasons=reasons,
                gemini_response=ai_assessment.model_dump() if ai_assessment else None,
                evaluated_by=evaluated_by,
            )
            db.add(new_assessment)
            await db.commit()

            logger.info("Successfully scanned and persisted URL: %s (Verdict: %s, Score: %d)", canonical, verdict, risk_score)
            return {
                "scan_id": str(scanned_record.id),
                "canonical_url": scanned_record.canonical_url,
                "domain": domain,
                "status": "EVALUATED",
                "verdict": verdict,
                "risk_score": risk_score,
                "confidence": confidence,
                "impersonated_brand": impersonated_brand,
                "reasons": reasons,
                "cached": False,
                "evaluated_by": evaluated_by,
            }
