"""
CLI script to create or promote an admin user in PostgreSQL.
Usage:
    python -m scripts.create_admin --email admin@example.com --password YourSecurePassword123!
"""

import argparse
import asyncio
import logging
import sys
import uuid

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import get_standalone_db_session
from app.modules.users.models import User

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("create_admin")


async def create_or_update_admin(email: str, password: str) -> None:
    clean_email = email.lower().strip()
    hashed = hash_password(password)

    async with get_standalone_db_session() as db:
        stmt = select(User).where(User.email == clean_email)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()

        if user:
            user.hashed_password = hashed
            user.role = "ADMIN"
            user.is_active = True
            await db.commit()
            logger.info("Successfully promoted existing user '%s' to ADMIN.", clean_email)
        else:
            new_user = User(
                id=uuid.uuid4(),
                email=clean_email,
                hashed_password=hashed,
                role="ADMIN",
                is_active=True,
            )
            db.add(new_user)
            await db.commit()
            logger.info("Successfully created new ADMIN user '%s'.", clean_email)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or promote an administrator user.")
    parser.add_argument("--email", required=True, help="Administrator email address")
    parser.add_argument("--password", required=True, help="Administrator secure password (min 8 chars)")

    args = parser.parse_args()

    if len(args.password) < 8:
        logger.error("Password must be at least 8 characters long.")
        sys.exit(1)

    asyncio.run(create_or_update_admin(args.email, args.password))


if __name__ == "__main__":
    main()
