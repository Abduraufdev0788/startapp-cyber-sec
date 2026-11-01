"""
Health check endpoints for Kubernetes and Docker probes.
"""

from typing import Annotated, Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/liveness")
async def liveness_check() -> dict[str, str]:
    """Returns 200 OK if the FastAPI process is alive and responsive."""
    return {"status": "ok"}


@router.get("/readiness")
async def readiness_check(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Any:
    """Verifies database and operational dependencies (PostgreSQL and Redis) readiness."""
    settings = get_settings()
    deps_status: dict[str, str] = {}
    is_healthy = True

    # 1. Verify PostgreSQL connection
    try:
        await db.execute(text("SELECT 1"))
        deps_status["database"] = "connected"
    except Exception as e:
        deps_status["database"] = f"unhealthy: {str(e)}"
        is_healthy = False

    # 2. Verify Redis connection
    redis_conn = None
    try:
        redis_conn = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_conn.ping()
        deps_status["redis"] = "connected"
    except Exception as e:
        deps_status["redis"] = f"unhealthy: {str(e)}"
        is_healthy = False
    finally:
        if redis_conn:
            await redis_conn.aclose()

    if not is_healthy:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "dependencies": deps_status,
            },
        )

    return {
        "status": "ready",
        "dependencies": deps_status,
    }
