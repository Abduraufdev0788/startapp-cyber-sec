"""
Unit tests for /api/v1/health endpoints and Redis-backed rate limiting.
"""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.rate_limit import rate_limit
from app.db.session import get_db_session
from app.main import app


@pytest.mark.asyncio
async def test_health_liveness_endpoint():
    """Tests GET /api/v1/health/liveness returns 200 OK."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health/liveness")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_readiness_healthy():
    """Tests GET /api/v1/health/readiness returns 200 when Postgres and Redis are reachable."""
    mock_db = AsyncMock()
    app.dependency_overrides[get_db_session] = lambda: mock_db

    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True

    try:
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/health/readiness")
                assert resp.status_code == 200
                data = resp.json()
                assert data["status"] == "ready"
                assert data["dependencies"]["database"] == "connected"
                assert data["dependencies"]["redis"] == "connected"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_readiness_unhealthy_on_db_or_redis_failure():
    """Tests GET /api/v1/health/readiness returns 503 when a dependency fails."""
    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("DB Connection refused")
    app.dependency_overrides[get_db_session] = lambda: mock_db

    mock_redis = AsyncMock()
    mock_redis.ping.side_effect = Exception("Redis unreachable")

    try:
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/api/v1/health/readiness")
                assert resp.status_code == 503
                data = resp.json()
                assert data["status"] == "unhealthy"
                assert "unhealthy" in data["dependencies"]["database"]
                assert "unhealthy" in data["dependencies"]["redis"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rate_limiter_exceeded():
    """Tests that exceeding the rate limit raises 429 Too Many Requests."""
    from fastapi import Depends, FastAPI
    from fastapi.responses import JSONResponse

    from app.core.exceptions import AppException

    test_app = FastAPI()

    @test_app.exception_handler(AppException)
    async def app_exception_handler(request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    limiter = rate_limit(times=2, seconds=60, key_prefix="test_rl")

    @test_app.get("/limited", dependencies=[Depends(limiter)])
    async def limited_route():
        return {"status": "ok"}

    mock_redis = AsyncMock()
    # 1st call -> count 1, 2nd call -> count 2, 3rd call -> count 3 (exceeded)
    mock_redis.incr.side_effect = [1, 2, 3]
    mock_redis.ttl.return_value = 55

    with patch("redis.asyncio.from_url", return_value=mock_redis):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp1 = await client.get("/limited")
            assert resp1.status_code == 200

            resp2 = await client.get("/limited")
            assert resp2.status_code == 200

            resp3 = await client.get("/limited")
            assert resp3.status_code == 429
            assert "Juda ko'p so'rov" in resp3.json()["error"]["message"]
