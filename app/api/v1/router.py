"""
API v1 Root Router.
Aggregates all sub-routers (health, scans, notifications, telegram, auth).
"""

from fastapi import APIRouter

from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.notifications import router as notifications_router
from app.api.v1.endpoints.scans import router as scans_router
from app.api.v1.endpoints.telegram import router as telegram_router

api_router = APIRouter(prefix="/v1")

# Mount endpoints
api_router.include_router(admin_router)
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(scans_router)
api_router.include_router(notifications_router)
api_router.include_router(telegram_router)
