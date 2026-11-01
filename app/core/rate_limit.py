"""
Redis-backed Rate Limiter dependency for FastAPI endpoints.
Protects authentication, scanning, and OTP verification endpoints against brute-force,
credential stuffing, and resource exhaustion / DoS attacks.
"""

import logging
from collections.abc import Callable
from typing import Any

import redis.asyncio as aioredis
from fastapi import Request, status

from app.core.config import get_settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


def rate_limit(
    times: int,
    seconds: int,
    key_prefix: str = "rl",
) -> Callable[[Request], Any]:
    """
    Returns a FastAPI dependency that enforces a rate limit using Redis.
    :param times: Maximum allowed requests within the time window.
    :param seconds: Sliding window duration in seconds.
    :param key_prefix: Distinct prefix for namespace isolation.
    """

    async def _rate_limiter_dependency(request: Request) -> None:
        settings = get_settings()

        # Extract client IP, respecting proxy forwarding headers if present
        forwarded_for = request.headers.get("x-forwarded-for")
        client_ip = forwarded_for.split(",")[0].strip() if forwarded_for else (
            request.client.host if request.client else "unknown"
        )

        # Unique key based on endpoint path and client IP
        path = request.url.path
        redis_key = f"{key_prefix}:{path}:{client_ip}"

        redis_client = None
        try:
            redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            # Atomic increment and expire setup
            current_requests = await redis_client.incr(redis_key)
            if current_requests == 1:
                await redis_client.expire(redis_key, seconds)

            if current_requests > times:
                ttl = await redis_client.ttl(redis_key)
                logger.warning(
                    "Rate limit exceeded: %s on %s (%d/%d, TTL: %ds)",
                    client_ip,
                    path,
                    current_requests,
                    times,
                    ttl,
                )
                raise AppException(
                    message=f"Juda ko'p so'rov yuborildi. Iltimos, {max(1, ttl)} soniyadan so'ng qayta urinib ko'ring.",
                    code="RATE_LIMIT_EXCEEDED",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    details=[{"retry_after_seconds": max(1, ttl)}],
                )
        except AppException:
            raise
        except Exception as e:
            # If Redis connection fails, log warning and fail open so application stays accessible
            logger.warning("Redis rate limiter check failed (failing open): %s", e)
        finally:
            if redis_client:
                try:
                    await redis_client.aclose()
                except Exception:
                    pass

    return _rate_limiter_dependency
