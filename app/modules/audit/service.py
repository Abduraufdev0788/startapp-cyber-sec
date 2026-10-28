"""
Security Audit Trail Service.
Provides tamper-evident event logging for authentication, account management, and threat responses.
"""

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Records security-sensitive operational actions into PostgreSQL."""

    @staticmethod
    async def log_event(
        db: AsyncSession,
        action: str,
        user_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """
        Persists an audit event entry.
        Common actions:
        - USER_REGISTER, USER_LOGIN, TOKEN_REFRESH
        - ACCOUNT_CONNECT, ACCOUNT_DISCONNECT
        - ALERT_DISMISSED, SSRF_BLOCKED, THREAT_RESCAN
        """
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
        )
        db.add(audit_entry)
        try:
            await db.commit()
            logger.info("Security audit event recorded: action=%s user_id=%s", action, user_id)
        except Exception as err:
            await db.rollback()
            logger.error("Failed to commit audit log event: %s", err, exc_info=True)

        return audit_entry
