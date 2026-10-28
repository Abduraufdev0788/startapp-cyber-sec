"""
Health check endpoints for Kubernetes and Docker probes.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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
    """Verifies database and operational dependencies readiness."""
    try:
        # Verify PostgreSQL connection
        await db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected",
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": f"error: {str(e)}",
            },
        )
