"""
FastAPI Main Application Entrypoint.
Initializes logging, middleware, global security exception handlers, and API routes.
"""

import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Preload all ORM models to configure SQLAlchemy mapper registry
import app.modules.audit.models  # noqa: F401
import app.modules.notifications.models  # noqa: F401
import app.modules.risk_engine.models  # noqa: F401
import app.modules.telegram_accounts.models  # noqa: F401
import app.modules.telegram_chats.models  # noqa: F401
import app.modules.threat_intelligence.models  # noqa: F401
import app.modules.url_scanning.models  # noqa: F401
import app.modules.users.models  # noqa: F401
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.lifecycle import seed_initial_admin
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle events management."""
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)
    logger.info("Starting %s in %s mode...", settings.PROJECT_NAME, settings.ENVIRONMENT)

    # Automatic initial administrator provisioning if none exists
    await seed_initial_admin()

    yield
    logger.info("Shutting down %s...", settings.PROJECT_NAME)


def create_application() -> FastAPI:
    """FastAPI application factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS if settings.ENVIRONMENT != "development" else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID and tracing middleware
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", f"req-{uuid.uuid4()}")
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Global handler for application-defined exceptions
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
                "meta": {
                    "request_id": request_id,
                },
            },
        )

    # Global handler for unhandled internal exceptions
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.error(
            "Unhandled server exception: %s (Request ID: %s)",
            str(exc),
            request_id,
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Investigation logged.",
                    "details": [],
                },
                "meta": {
                    "request_id": request_id,
                },
            },
        )

    # Mount API v1
    app.include_router(api_router, prefix="/api")

    # Mount static assets and Web Dashboards
    import mimetypes
    import os

    from fastapi.responses import FileResponse, RedirectResponse
    from fastapi.staticfiles import StaticFiles

    # Ensure reliable MIME types on all Linux server distributions
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("text/css", ".css")
    mimetypes.add_type("text/html", ".html")

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir, html=True), name="static")

    admin_dir = os.path.join(static_dir, "admin")
    admin_index_file = os.path.join(admin_dir, "index.html")
    admin_login_file = os.path.join(admin_dir, "login.html")

    @app.get("/login", include_in_schema=False)
    @app.get("/login/", include_in_schema=False)
    async def login_page():
        if os.path.exists(admin_login_file):
            return FileResponse(admin_login_file, media_type="text/html")
        return JSONResponse(status_code=404, content={"message": "Login page frontend not found"})

    @app.get("/admin", include_in_schema=False)
    @app.get("/admin/", include_in_schema=False)
    @app.get("/dashboard", include_in_schema=False)
    @app.get("/dashboard/", include_in_schema=False)
    async def admin_dashboard():
        if os.path.exists(admin_index_file):
            return FileResponse(admin_index_file, media_type="text/html")
        return JSONResponse(status_code=404, content={"message": "Admin dashboard frontend not found"})

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    return app


app = create_application()
