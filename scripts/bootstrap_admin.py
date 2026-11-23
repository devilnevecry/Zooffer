"""Promote an existing Telegram account to staff (first administrator bootstrap).

There is no public way to create an administrator: roles are only changed by an
existing superadmin or by this one-shot script, which requires the
``ADMIN_BOOTSTRAP_TOKEN`` secret.

Usage (from the repository root):

    $env:ADMIN_BOOTSTRAP_TOKEN = "<long random secret>"
    .venv\\Scripts\\python scripts\\bootstrap_admin.py --telegram-id 123456789
    .venv\\Scripts\\python scripts\\bootstrap_admin.py --public-id <uuid> --role admin

The account must already exist: open the bot, send /start and accept the terms
first. After bootstrapping, sign in on the website and enable two-factor
authentication in account settings, then clear ADMIN_BOOTSTRAP_TOKEN.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from sqlalchemy import select
from zooffer.config import settings
from zooffer.core.enums import UserRole
from zooffer.db.models import AuditLog, AuthIdentity, User
from zooffer.db.session import SessionLocal, dispose_engine

STAFF_ROLES = {
    UserRole.MODERATOR.value,
    UserRole.ADMIN.value,
    UserRole.SUPERADMIN.value,
}


async def bootstrap(
    *, telegram_id: str | None, public_id: str | None, role: str
) -> None:
    if not settings.admin_bootstrap_token:
        raise SystemExit(
            "ADMIN_BOOTSTRAP_TOKEN is not set. Generate a secret and export it before running."
        )
    async with SessionLocal() as db:
        user: User | None = None
        if telegram_id:
            identity = await db.scalar(
                select(AuthIdentity).where(
                    AuthIdentity.provider == "telegram",
                    AuthIdentity.provider_user_id == telegram_id,
                )
            )
            if identity is not None:
                user = await db.get(User, identity.user_id)
        elif public_id:
            user = await db.scalar(
                select(User).where(User.public_id == UUID(public_id))
            )
        if user is None:
            raise SystemExit(
                "Account not found. Open the bot, send /start and accept the terms first."
            )
        previous = user.role
        user.role = role
        db.add(
            AuditLog(
                id=uuid4(),
                actor_id=user.id,
                actor_role=role,
                action="admin.bootstrap",
                object_type="user",
                object_id=str(user.public_id),
                metadata_json={"previous_role": previous, "new_role": role},
            )
        )
        await db.commit()
        print(f"Role updated: {user.public_id} {previous} -> {role}")
        if not user.mfa_enabled:
            print(
                "Next step: sign in on the website and enable two-factor authentication."
            )
        print("Then clear ADMIN_BOOTSTRAP_TOKEN from the environment.")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap the first Zooffer administrator."
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--telegram-id", help="Numeric Telegram user id of the account")
    target.add_argument("--public-id", help="Zooffer public UUID of the account")
    parser.add_argument(
        "--role", default=UserRole.SUPERADMIN.value, choices=sorted(STAFF_ROLES)
    )
    args = parser.parse_args()
    try:
        await bootstrap(
            telegram_id=args.telegram_id, public_id=args.public_id, role=args.role
        )
    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
