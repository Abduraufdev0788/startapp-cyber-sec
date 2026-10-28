"""
Celery URL background scan and risk analysis task.
Executes SSRF check, technical enrichment, Gemini structured assessment, risk scoring,
and automatically triggers active notification alerts if risk exceeds threshold.
"""

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.v1.endpoints.notifications import defang_url
from app.db.session import get_standalone_db_session
from app.integrations.gemini.client import GeminiClient
from app.modules.notifications.models import Notification
from app.modules.risk_engine.engine import RiskEngine
from app.modules.risk_engine.models import ThreatAssessment
from app.modules.threat_intelligence.models import ThreatIntelligence
from app.modules.threat_intelligence.service import ThreatIntelligenceService
from app.modules.url_scanning.models import ScannedUrl
from app.modules.url_scanning.pipeline import compute_url_hash
from app.workers.celery_app import celery_app
from app.workers.tasks.notify import dispatch_alert_task

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.workers.tasks.scan.scan_url",
    max_retries=2,
    default_retry_delay=10,
)
def scan_url_background(
    self,
    canonical_url: str,
    user_id_str: str,
    chat_id: int,
    chat_title: str,
    user_telegram_id: int | None = None,
) -> dict:
    """Performs background URL threat evaluation and queues alert if dangerous."""

    async def _run_scan() -> dict:
        user_id = uuid.UUID(user_id_str)
        url_hash = compute_url_hash(canonical_url)

        async with get_standalone_db_session() as db:
            # 1. Check existing cached scan in DB
            stmt = (
                select(ScannedUrl)
                .where(ScannedUrl.url_hash == url_hash)
                .options(selectinload(ScannedUrl.threat_assessment))
            )
            res = await db.execute(stmt)
            scanned_record = res.scalar_one_or_none()

            if scanned_record and scanned_record.threat_assessment:
                assessment = scanned_record.threat_assessment
                verdict = assessment.verdict
                risk_score = assessment.risk_score
                impersonated_brand = assessment.impersonated_brand
                reasons = assessment.reasons
            else:
                # 2. Fresh enrichment with SSRF protection
                evidence = await ThreatIntelligenceService.enrich_url(canonical_url)
                domain = evidence["domain"]

                # 3. Gemini AI Analysis (with heuristic fallback)
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

                # 4. Multi-factor Risk Engine
                risk_result = RiskEngine.evaluate(
                    domain=domain,
                    technical_evidence=evidence,
                    ai_assessment=ai_assessment,
                )
                verdict = risk_result["verdict"]
                risk_score = risk_result["risk_score"]
                impersonated_brand = risk_result["impersonated_brand"]
                reasons = risk_result["reasons"]

                # 5. Save to PostgreSQL
                if not scanned_record:
                    scanned_record = ScannedUrl(
                        url_hash=url_hash,
                        raw_url=canonical_url,
                        canonical_url=canonical_url,
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
                    confidence=risk_result["confidence"],
                    impersonated_brand=impersonated_brand,
                    reasons=reasons,
                    gemini_response=ai_assessment.model_dump() if ai_assessment else None,
                    evaluated_by=evaluated_by,
                )
                db.add(new_assessment)
                await db.commit()

            # 6. If high threat (risk_score >= 60), check Redis deduplication & throttle
            if risk_score >= 60:
                import redis.asyncio as aioredis

                from app.core.config import get_settings

                alert_type = "CRITICAL_PHISHING" if risk_score >= 80 else "SCAM_WARNING"
                settings = get_settings()

                is_throttled = False
                redis_conn = None
                try:
                    redis_conn = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
                    dedup_key = f"alert_sent:{user_id}:{url_hash}"
                    already_sent = await redis_conn.get(dedup_key)
                    if already_sent:
                        is_throttled = True
                        logger.info("Alert throttled for user %s and URL %s (sent within last hour)", user_id, url_hash)
                    else:
                        await redis_conn.set(dedup_key, "1", ex=3600)  # 1 hour TTL
                except Exception as redis_err:
                    logger.warning("Redis check failed in scan task: %s", redis_err)
                finally:
                    if redis_conn:
                        await redis_conn.aclose()

                notif = Notification(
                    user_id=user_id,
                    url_id=scanned_record.id,
                    telegram_chat_id=chat_id,
                    alert_type=alert_type,
                    delivery_status="THROTTLED" if is_throttled else "PENDING",
                    is_dismissed=False,  # Active alert stays in app until dismissed
                )
                db.add(notif)
                await db.commit()

                # Dispatch Telegram alert via bot only if not throttled
                if not is_throttled:
                    recipient_id = user_telegram_id if user_telegram_id is not None else chat_id
                    dispatch_alert_task.delay(
                        alert_id=str(notif.id),
                        chat_id=recipient_id,
                        chat_title=chat_title,
                        defanged_url=defang_url(canonical_url),
                        risk_score=risk_score,
                        impersonated_brand=impersonated_brand,
                        reasons=reasons,
                    )

            return {
                "verdict": verdict,
                "risk_score": risk_score,
                "impersonated_brand": impersonated_brand,
            }

    return asyncio.run(_run_scan())
