"""
Application Lifecycle Management.
Handles startup initialization, database verification, and automatic default administrator seeding.
"""

import logging
import uuid

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import get_standalone_db_session
from app.modules.users.models import User

logger = logging.getLogger(__name__)


async def seed_initial_admin() -> None:
    """
    Ensures an administrator user exists if configured in environment variables.
    If INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD are provided and no admin exists,
    creates the administrator account.
    """
    settings = get_settings()
    if not settings.INITIAL_ADMIN_EMAIL or not settings.INITIAL_ADMIN_PASSWORD:
        return

    admin_email = settings.INITIAL_ADMIN_EMAIL.lower().strip()
    admin_password = settings.INITIAL_ADMIN_PASSWORD

    if len(admin_password) < 8:
        logger.warning("INITIAL_ADMIN_PASSWORD must be at least 8 characters. Skipping auto-seed.")
        return

    try:
        async with get_standalone_db_session() as db:
            stmt = select(User).where(User.role == "ADMIN")
            result = await db.execute(stmt)
            existing_admin = result.scalar_one_or_none()

            if existing_admin:
                logger.info(
                    "Administrator account already exists in database (%s). Skipping auto-seed.",
                    existing_admin.email,
                )
                return

            logger.info("No administrator found. Seeding default administrator: %s", admin_email)
            hashed = hash_password(admin_password)
            new_admin = User(
                id=uuid.uuid4(),
                email=admin_email,
                hashed_password=hashed,
                role="ADMIN",
                is_active=True,
            )
            db.add(new_admin)
            await db.commit()
            logger.info(
                "Initial administrator account '%s' successfully provisioned.",
                admin_email,
            )
    except Exception as exc:
        logger.warning(
            "Auto-seed administrator check deferred (database may still be initializing or running migrations): %s",
            exc,
        )

