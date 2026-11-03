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
    Ensures at least one administrator user exists on platform initialization.
    If no user with role 'ADMIN' exists, creates the default admin user configured in Settings.
    """
    settings = get_settings()
    admin_email = settings.INITIAL_ADMIN_EMAIL.lower().strip()
    admin_password = settings.INITIAL_ADMIN_PASSWORD

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

